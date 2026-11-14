#pragma once
#ifdef __cplusplus
extern "C" {
#endif
/* Copies a completed reply into a bounded queue; never performs HTTP here. */
void muse_pi_bridge_enqueue(const char *text);
/* Copies a live voice state to the existing asynchronous HTTP queue. */
void muse_pi_bridge_enqueue_status(const char *state); /* MUSE_PI_LIVE_STATUS_V1 */
#ifdef __cplusplus
}
#endif
