# Phase 9 — Experimental hands-free TTS interruption

**Branch:** `feature/phase9-voice-barge-in-2026-11` (based on Phase 8)
**Status:** Code staged for build verification; NOT hardware-tested.
**Hardware:** Waveshare ESP32-S3-Touch-AMOLED-1.75-B (`s3n`). Raspberry Pi bridge optional.

## Objective

When Fish Audio is already speaking, detect an external human saying "Hey Muse" through the Phase 8 AEC-cleaned microphone stream. Cancel the existing Fish Audio turn, stop the AEC worker, and start the existing hands-free voice recording path. Do not trigger on the speaker's own "Hey Muse" audio.

## Safety boundaries

- Opt-in only: `CONFIG_MUSE_TTS_BARGE_IN=y` in a separate Phase 9 test image, NOT in Phase 8 or stable images.
- AEC worker only **latches** a detection. `muse_voice` owns playback cancellation and mode changes.
- On a human wake, `muse_tts_wake_observer_stop()` completes *before* requesting a new microphone recording. If the worker does not exit, automatic recording is aborted.
- Normal push-to-talk interruption remains unchanged.
- Reuse `record(barge_in=true, hands_free=true)` with its existing 200 ms speaker-tail settling. The user should say the question **after** the wake phrase, allowing time for TTS to stop.
- No change to Raspberry Pi display/e-paper data paths.
- Hardware test MUST retain a full flash backup and stable rollback path.

## Build (Mac, from repository root)

```sh
git switch feature/phase9-voice-barge-in-2026-11
git pull --ff-only
cd esp32
MUSE_PI_BRIDGE=1 MUSE_AEC_TEST=1 MUSE_BARGE_TEST=1 tools/muse/board.sh build s3n
```

The separate build output is `build-muse-waveshare-s3-175-pi-aec-test-barge-test`.
**Build first. Do not flash or merge until the build and code review pass.**

## First on-device test (only after build/code review approval)

1. Back up the existing full 16MB flash image before writing the Phase 9 experimental image.
2. Confirm Phase 8 human/speaker separation at normal volume.
3. Ask Muse for a ~30 second spoken response, then say "Hey Muse" once while it is speaking.
4. Expect the `Phase 9: AEC wake -> stopping TTS` log, audio interruption, `LISTENING` mode, and a new response to a follow-up question.
5. Repeat at lower/higher volume. Have Fish Audio say "Hey Muse" without human speech; it must NOT interrupt.
6. Confirm button interruption still works; idle wake still works; Raspberry Pi status/reply still works.
7. Monitor internal heap, timeouts, stale speaker audio and repeated interruptions. Roll back if unstable.

## Known limitations

- AEC reference-to-mic timing remains uncalibrated. Phase 8 tests were encouraging, but do not guarantee zero false positives in every acoustic environment.
- Limited largest internal heap block (~3–4KB while AEC active) may lead to failures during network or audio activity.
- No auto-confirmation of human origin; uses the existing wake model's detection after AEC.
- Current implementation stops TTS **after** recognizing the complete wake phrase, not mid-syllable.
- Cloud response/transport may be delayed by unrelated Link tunnel resets.
