#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "sdkconfig.h"

#if CONFIG_MUSE_TTS_WAKE_OBSERVER
#ifdef __cplusplus
extern "C" {
#endif
void muse_tts_wake_observer_start(void);
void muse_tts_wake_observer_stop(void);
void muse_tts_wake_observer_reference(const int16_t *pcm, size_t frames);
bool muse_tts_wake_observer_detected(void);
/* Phase 9: consume one human wake detection once; only enabled in barge test builds. */
bool muse_tts_wake_observer_take_barge(void);
/* A new mic recording must not start while the AEC worker is still reading. */
bool muse_tts_wake_observer_quiescent(void);
#ifdef __cplusplus
}
#endif
#else
static inline void muse_tts_wake_observer_start(void) {}
static inline void muse_tts_wake_observer_stop(void) {}
static inline void muse_tts_wake_observer_reference(const int16_t *pcm, size_t frames) {(void)pcm; (void)frames;}
static inline bool muse_tts_wake_observer_detected(void) {return false;}
static inline bool muse_tts_wake_observer_take_barge(void) {return false;}
static inline bool muse_tts_wake_observer_quiescent(void) {return true;}
#endif
