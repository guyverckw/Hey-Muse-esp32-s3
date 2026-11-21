#pragma once
/* The bridge is optional. Standalone builds compile these calls away:
 * no Pi HTTP worker, URL, token, or queue is linked into the firmware. */
#include "sdkconfig.h"
#ifdef __cplusplus
extern "C" {
#endif

#if CONFIG_MUSE_PI_BRIDGE
/* Copies a completed reply into a bounded queue; never performs HTTP here. */
void muse_pi_bridge_enqueue(const char *text);
/* Copies a live voice state to the existing asynchronous HTTP queue. */
void muse_pi_bridge_enqueue_status(const char *state);
#else
static inline void muse_pi_bridge_enqueue(const char *text) {
    (void)text;
}
static inline void muse_pi_bridge_enqueue_status(const char *state) {
    (void)state;
}
#endif

#ifdef __cplusplus
}
#endif
