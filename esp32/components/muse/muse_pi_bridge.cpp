#include "muse_pi_bridge.h"
#include "muse_pi_bridge_config.h"
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include "cJSON.h"
#include "esp_log.h"
#include "esp_http_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

static const char *TAG = "muse_pi_bridge";
static QueueHandle_t s_queue = nullptr;

struct Reply { char *text; bool is_status; }; /* MUSE_PI_LIVE_STATUS_V1 */

static void worker(void *) {
    Reply msg{};
    for (;;) {
        if (xQueueReceive(s_queue, &msg, portMAX_DELAY) != pdTRUE) continue;
        if (!msg.text) continue;
        /* JSON-escape UTF-8 safely using cJSON; output is UTF-8. */
        cJSON *payload = cJSON_CreateObject();
        if (payload) {
            if (msg.is_status) {
                cJSON_AddStringToObject(payload, "state", msg.text);
            } else {
                cJSON_AddStringToObject(payload, "text", msg.text);
                cJSON_AddStringToObject(payload, "source", "esp32");
            }
            char *json = cJSON_PrintUnformatted(payload);
            cJSON_Delete(payload);
            if (json) {
                esp_http_client_config_t cfg = {};
                // Both requests use the existing private URL and Bearer token.
                char status_url[256] = {};
                if (msg.is_status) {
                    snprintf(status_url, sizeof(status_url), "%s", MUSE_PI_BRIDGE_URL);
                    char *suffix = strstr(status_url, "/api/v1/reply");
                    if (!suffix) {
                        ESP_LOGW(TAG, "Unexpected reply endpoint; status skipped");
                        free(json);
                        free(msg.text);
                        continue;
                    }
                    snprintf(suffix, sizeof(status_url) - (size_t)(suffix - status_url), "/api/v1/status");
                }
                cfg.url = msg.is_status ? status_url : MUSE_PI_BRIDGE_URL;
                cfg.timeout_ms = 2500;
                esp_http_client_handle_t client = esp_http_client_init(&cfg);
                if (client) {
                    esp_http_client_set_method(client, HTTP_METHOD_POST);
                    esp_http_client_set_header(client, "Content-Type", "application/json; charset=utf-8");
                    esp_http_client_set_header(client, "Authorization", "Bearer " MUSE_PI_BRIDGE_TOKEN);
                    esp_http_client_set_post_field(client, json, (int)strlen(json));
                    esp_err_t err = esp_http_client_perform(client);
                    int status = esp_http_client_get_status_code(client);
                    if (err == ESP_OK && status == 202) {
                        ESP_LOGI(TAG, "%s delivered to Raspberry Pi (%d)", msg.is_status ? "Status" : "Reply", status);
                    } else {
                        ESP_LOGW(TAG, "Raspberry Pi %s failed: %s, HTTP %d", msg.is_status ? "status" : "reply", esp_err_to_name(err), status);
                    }
                    esp_http_client_cleanup(client);
                }
                free(json);
            }
        }
        free(msg.text);
    }
}

static void enqueue_item(const char *text, bool is_status) {
    if (!text || !text[0]) return;
    /* No network I/O or blocking in the Muse chat callback. */
    if (!s_queue) {
        s_queue = xQueueCreate(6, sizeof(Reply));
        if (!s_queue) { ESP_LOGW(TAG, "Could not create reply queue"); return; }
        BaseType_t ok = xTaskCreate(worker, "pi_bridge", 6144, nullptr, 4, nullptr);
        if (ok != pdPASS) { ESP_LOGW(TAG, "Could not create bridge worker"); vQueueDelete(s_queue); s_queue = nullptr; return; }
    }
    /* Bounded to the same per-message capacity as Muse captions. */
    size_t len = strnlen(text, is_status ? 16 : 1023);
    char *copy = (char *)malloc(len + 1);
    if (!copy) { ESP_LOGW(TAG, "Out of memory copying reply"); return; }
    memcpy(copy, text, len);
    copy[len] = 0;
    Reply msg{copy, is_status};
    if (xQueueSend(s_queue, &msg, 0) != pdTRUE) {
        free(copy);
        ESP_LOGW(TAG, "Reply queue full; skipping this reply");
    }
}

/* MUSE_PI_LIVE_STATUS_V1: reuse existing queue/worker; never block the voice task. */
extern "C" void muse_pi_bridge_enqueue(const char *text) {
    enqueue_item(text, false);
}
extern "C" void muse_pi_bridge_enqueue_status(const char *state) {
    if (!state || (strcmp(state, "idle") && strcmp(state, "listening") &&
                   strcmp(state, "thinking") && strcmp(state, "speaking") &&
                   strcmp(state, "error"))) return;
    enqueue_item(state, true);
}
