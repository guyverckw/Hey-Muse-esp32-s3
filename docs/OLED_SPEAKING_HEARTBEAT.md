# OLED SPEAKING heartbeat during long Fish Audio replies

**Status:** development branch prepared; not built or flashed yet. Do not change the Pi's tested 180-second e-paper cooldown.

## Physical results — November 15, 2026

The user confirms **full long-response speech now works completely**, and the Pi receives the complete reply for e-paper pagination. However, during an extended reply the Pi OLED switches from SPEAKING to READY before actual speech finishes.

The root cause is a status-liveness mismatch:
- `raspberry-pi/muse_pi.py` resets a transient status to idle after **90 seconds** without new status messages (`LIVE_STATUS_TIMEOUT = 90.0`).
- `esp32/components/muse/muse_voice.c` previously emitted SPEAKING once on the first PCM audio, and IDLE when playback ended.
- Fish Audio now synthesises long speech over several chunks; the board may legitimately be speaking for longer than 90 seconds without a fresh status update.

## Change

In `hatch_reply()`, after starting audio, send another asynchronous `muse_pi_bridge_enqueue_status("speaking")` every **20 seconds**, including the gaps between Fish Audio chunks. No network request is made synchronously in the audio loop: the existing Pi bridge queue handles delivery in its separate worker. On completion, the existing `go_idle()` path emits IDLE so the OLED switches to READY. The existing Pi 90-second expiry remains a safety fallback if the board crashes, disconnects or stops sending messages. This change does not change audio generation, speech buffer sizes, Pi e-paper or playback timings.

- New branch: `feature/oled-speaking-heartbeat-2026-11`.
- Recovery reference: `backup/full-length-tts-user-tested-2026-11` retains the exact code used for the user's confirmed full-length audio/e-paper success.
- Previously created 16 MB on-device firmware backup remains available locally and confidential.

## Mac verification (do not flash until all build checks pass)

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
git status --short
git fetch origin
git switch --track origin/feature/oled-speaking-heartbeat-2026-11
python3 -m unittest esp32/tests/test_voice_status_heartbeat.py
. ~/esp/esp-idf-v6/export.sh
cd esp32
tools/muse/board.sh build s3n
```

If the branch was already switched locally, use `git switch feature/oled-speaking-heartbeat-2026-11` followed by `git pull --ff-only`. Preserve uncommitted changes rather than forcing a checkout.

After verifying native test, successful build, firmware backup, and stable audio, flash **only if user is ready**:

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3/esp32
tools/muse/board.sh flash s3n
```

## Physical acceptance

1. Short voice: LISTENING → THINKING → SPEAKING → READY, complete spoken reply.
2. Long (>90-second) answer: OLED remains SPEAKING throughout playback, including chunk gaps; then READY only after actual speech ends.
3. Pi logs: authenticated status HTTP 202 requests at ~20-second intervals while speaking; one idle event afterward. No tokens in logs pasted to chat.
4. Pi still receives the entire answer; LEFT/RIGHT navigation respects the 180-second e-paper cooldown.
5. No unexpected ESP32 or Pi resets, no speech omissions.

**No hardware success should be recorded before the user's testing.**
