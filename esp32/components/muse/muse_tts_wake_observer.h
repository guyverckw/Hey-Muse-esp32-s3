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
#ifdef __cplusplus
}
#endif
#else
static inline void muse_tts_wake_observer_start(void) {}
static inline void muse_tts_wake_observer_stop(void) {}
static inline void muse_tts_wake_observer_reference(const int16_t *pcm, size_t frames) {(void)pcm; (void)frames;}
static inline bool muse_tts_wake_observer_detected(void) {return false;}
#endif
