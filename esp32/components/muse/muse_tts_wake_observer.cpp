/* Experimental Phase 8 AEC / wake observer.
 * Enabled ONLY in CONFIG_MUSE_TTS_WAKE_OBSERVER test builds.
 * Does not cancel playback, change recording state, or contact Raspberry Pi.
 * The speaker reference is taken from the actual PCM supplied to the codec;
 * acoustic/DMA delay is not calibrated. Rejecting speaker-only "Hey Muse"
 * MUST be confirmed on the physical board before implementing barge-in.
 */
#include "muse_tts_wake_observer.h"

#if CONFIG_MUSE_TTS_WAKE_OBSERVER

#include <cstring>
#include <cstdlib>

#include "esp_aec.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "muse_audio.h"
#include "muse_wake.h"

namespace {
constexpr size_t kAudioFrames = MUSE_AUDIO_CHUNK; // 320 / 20ms
constexpr size_t kMaxAecFrames = 1024;
constexpr uint32_t kLabelMs = 3000;
constexpr size_t kQueueDepth = 20;
const char *TAG = "tts_aec_test";

struct RefChunk {
    int16_t pcm[kAudioFrames];
    uint16_t frames;
};
QueueHandle_t s_refs = nullptr;
volatile bool s_running = false;
volatile bool s_worker_alive = false;
volatile uint32_t s_detected_until_ms = 0;
uint32_t s_overflows = 0;

alignas(16) int16_t s_mic[kMaxAecFrames];
alignas(16) int16_t s_ref[kMaxAecFrames];
alignas(16) int16_t s_clean[kMaxAecFrames];

void monitor_task(void *)
{
    aec_handle_t *aec = aec_create(16000, 4, 1, AEC_MODE_FD_LOW_COST);
    if (!aec) {
        ESP_LOGE(TAG, "AEC init failed (memory or component), no monitoring");
        s_running = false;
        s_worker_alive = false;
        vTaskDelete(nullptr);
        return;
    }
    const int frames = aec_get_chunksize(aec);
    if (frames <= 0 || frames > static_cast<int>(kMaxAecFrames)) {
        ESP_LOGE(TAG, "Unsupported AEC frame size: %d", frames);
        aec_destroy(aec);
        s_running = false;
        s_worker_alive = false;
        vTaskDelete(nullptr);
        return;
    }

    ESP_LOGI(TAG, "AEC observer active: frame=%d samples, no TTS cancellation", frames);
    int offset = 0;
    while (s_running) {
        int16_t mic[kAudioFrames];
        if (muse_audio_read(mic, kAudioFrames) != ESP_OK) {
            ESP_LOGW(TAG, "Microphone read failed; monitoring stopped");
            break;
        }
        RefChunk ref = {};
        // The outgoing PCM queue is deliberately best-effort. Missing chunks
        // mean unaligned reference; physical test results are then inconclusive.
        bool has_ref = xQueueReceive(s_refs, &ref, 0) == pdTRUE;
        size_t n = has_ref ? ref.frames : 0;
        if (!has_ref) {
            // Count missed references separately from queue overflows.
            ++s_overflows;
        }
        for (size_t i = 0; i < kAudioFrames; ++i) {
            s_mic[offset] = mic[i];
            s_ref[offset] = (i < n) ? ref.pcm[i] : 0;
            ++offset;
            if (offset == frames) {
                aec_process(aec, s_mic, s_ref, s_clean);
                if (muse_wake_process(s_clean, frames)) {
                    s_detected_until_ms = static_cast<uint32_t>(esp_timer_get_time() / 1000) + kLabelMs;
                    ESP_LOGW(TAG, "DETECTED on AEC output; verify external speech, not speaker echo");
                    muse_wake_reset(); // require another complete wake phrase
                }
                offset = 0;
            }
        }
    }
    ESP_LOGI(TAG, "AEC observer stopped; missing/overflow references=%lu",
             static_cast<unsigned long>(s_overflows));
    aec_destroy(aec);
    s_worker_alive = false;
    vTaskDelete(nullptr);
}
} // namespace

extern "C" void muse_tts_wake_observer_start(void)
{
    if (s_running || !muse_wake_enabled()) return;
    s_detected_until_ms = 0;
    s_overflows = 0;
    s_refs = xQueueCreate(kQueueDepth, sizeof(RefChunk));
    if (!s_refs) {
        ESP_LOGE(TAG, "Reference queue allocation failed");
        return;
    }
    muse_wake_reset();
    s_running = true;
    s_worker_alive = true;
    if (xTaskCreate(monitor_task, "tts_aec_observer", 8192, nullptr, 5, nullptr) != pdPASS) {
        ESP_LOGE(TAG, "AEC worker creation failed");
        s_running = s_worker_alive = false;
        vQueueDelete(s_refs);
        s_refs = nullptr;
    }
}

extern "C" void muse_tts_wake_observer_reference(const int16_t *pcm, size_t frames)
{
    if (!s_running || !s_refs || !pcm || !frames) return;
    RefChunk chunk = {};
    chunk.frames = static_cast<uint16_t>(frames > kAudioFrames ? kAudioFrames : frames);
    memcpy(chunk.pcm, pcm, chunk.frames * sizeof(int16_t));
    if (xQueueSend(s_refs, &chunk, 0) != pdTRUE) {
        // Keep the newest reference. Never block the audio playback writer.
        RefChunk stale;
        xQueueReceive(s_refs, &stale, 0);
        if (xQueueSend(s_refs, &chunk, 0) != pdTRUE) ++s_overflows;
        else ++s_overflows;
    }
}

extern "C" bool muse_tts_wake_observer_detected(void)
{
    if (!s_running) return false;
    const uint32_t now = static_cast<uint32_t>(esp_timer_get_time() / 1000);
    return static_cast<int32_t>(s_detected_until_ms - now) > 0;
}

extern "C" void muse_tts_wake_observer_stop(void)
{
    if (!s_running && !s_worker_alive) return;
    s_running = false;
    for (unsigned i = 0; i < 120 && s_worker_alive; ++i) {
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    if (s_worker_alive) {
        ESP_LOGE(TAG, "Observer worker did not exit; leaving reference queue allocated");
        return;
    }
    if (s_refs) {
        vQueueDelete(s_refs);
        s_refs = nullptr;
    }
}
#endif
