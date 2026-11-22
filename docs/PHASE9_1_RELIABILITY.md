# Phase 9.1 — AEC reliability and memory diagnostics

**Base:** `feature/phase9-voice-barge-in-2026-11` (tested on hardware by user)
**Candidate:** `feature/phase9-1-aec-reliability-2026-11`
**Status:** Code committed. Build and on-device verification pending.

## Scope

No changes to the timing, wake-word model, or barge-in control flow.

- Fish Audio PCM callback refusal is logged as an *expected consumer stop* rather than a failed Fish Audio request. All other errors remain warnings.
- AEC reports **missing reference chunks** separately from **overwritten reference queue chunks**, plus total AEC frames processed. An empty reference queue and a dropped stale queue entry are distinct events.
- AEC reports internal RAM free/largest contiguous block and PSRAM free after releasing AEC and its queue.
- The queue overflow counter uses atomic builtins because audio output and AEC monitoring run on separate tasks.

These changes improve observability; they do not claim to resolve all memory fragmentation, misalignment, or tunnel reset issues.

## Build only (do not flash until build passes)

```sh
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
git fetch origin
git switch feature/phase9-1-aec-reliability-2026-11
git pull --ff-only
cd esp32
MUSE_PI_BRIDGE=1 MUSE_AEC_TEST=1 MUSE_BARGE_TEST=1 tools/muse/board.sh build s3n
grep -E 'error:|undefined reference|CMake Error|Project build complete' /tmp/muse_build_s3n_1.log | tail -20
```

The Phase 9.1 build uses the same isolated barge-test directory as Phase 9. Keep the proven Phase 9 binary/flash backup available before flashing any new build.

## Later hardware test checklist

1. Confirm one normal wake, voice question, Fish Audio reply.
2. Complete 3 voice barge-ins in succession. Each interruption must initiate hands-free recording without a button.
3. Fish Audio self-wake: request "Hey Muse" 20 times and remain silent; expect zero interruptions.
4. Press hardware button during TTS, then verify normal recording.
5. Let a 2–3 minute spoken response play without speaking. Inspect end-of-run missing references and queue overwrites.
6. Repeat at least 10–20 short turns, record the AEC start and release heap lines, and compare initial vs final idle internal memory and PSRAM. Look for persistent downward drift, resets, watchdog errors, and allocation failures.
7. Monitor Wi-Fi / Link tunnel resets separately; this phase does not modify the tunnel layer.

### Expected new diagnostics

- `Fish Audio PCM consumer stopped playback (turn cancelled or superseded)`
- `AEC observer stopped: AEC frames=N, missing reference chunks=N, overwritten queue chunks=N`
- `AEC released heap: internal free=N largest=N, PSRAM free=N`

### Rollback

Switch back to the tested `feature/phase9-voice-barge-in-2026-11` branch, rebuild with `MUSE_PI_BRIDGE=1 MUSE_AEC_TEST=1 MUSE_BARGE_TEST=1`, and flash only after verifying the backup. Do not erase NVS.

### Outstanding risks

- The largest contiguous internal heap block during AEC is only about 3–4KB.
- Incomplete speaker reference data prevents valid wake processing for some frames.
- AEC-to-speaker delay has not been calibrated.
- Shutdown task scheduling and shared mic ownership need soak testing across repeated interruptions.
- Cloud Link tunnel resets remain unrelated and unresolved.
