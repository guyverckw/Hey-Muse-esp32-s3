# Phase 8 — AEC-filtered wake-word observer (EXPERIMENTAL)

**Status: source prepared, NOT built on user's Mac and NOT hardware-validated.**
Do not merge this test branch into the physically accepted stable firmware.

## Scope

On the Waveshare ESP32-S3-Touch-AMOLED-1.75-B (`s3n`), during Fish Audio playback only:
- A dedicated diagnostic worker reads mic PCM and uses ESP-SR 2.6.1 AEC (`AEC_MODE_FD_LOW_COST`) with the outgoing speaker PCM as reference.
- Cleaned audio is passed to the existing "Hey Muse" model.
- A detection temporarily shows **DETECTED** in place of **SPEAKING** for about 3 seconds; serial logging also reports detection.
- TTS remains active; **no hands-free interruption is implemented**.
- Existing push-button interruption, Muse chat, and optional Pi bridge are unchanged.
- A normal build has the diagnostic disabled and no ESP-SR dependency.

## Build on the Mac (no flash first)

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
git fetch origin
git switch feature/phase8-aec-wake-observer-2026-11
cd esp32
. ~/esp/esp-idf-v6/export.sh
# Use this if the installed ESP-IDF is in the user's confirmed directory.
# Separate diagnostic build directory, standalone mode:
MUSE_AEC_TEST=1 tools/muse/board.sh build s3n
```

For Pi-enabled test images (preserving the existing local private Pi config header):
```bash
MUSE_PI_BRIDGE=1 MUSE_AEC_TEST=1 tools/muse/board.sh build s3n
```

Build output: `build-muse-waveshare-s3-175-aec-test/` (standalone) or `build-muse-waveshare-s3-175-pi-aec-test/` (Pi-enabled). Both are distinct from earlier stable build directories. The script logs to `/tmp/muse_build_s3n_0.log` or `/tmp/muse_build_s3n_1.log`. Review any errors before considering a flash.

Do **not flash unless accepting the risk of temporarily replacing the working firmware**. The user has no spare board; an actual test requires replacing the firmware on the one physical board and later restoring the saved known-good image.

If a build succeeds and the user chooses to test physical hardware:
```bash
MUSE_PI_BRIDGE=1 MUSE_AEC_TEST=1 tools/muse/board.sh flash s3n
```
Use the same MUSE_PI_BRIDGE value at flash as at build. Omit `MUSE_PI_BRIDGE=1` if built standalone.

## Board test (only after explicit decision to flash)

1. First verify normal voice conversation and button interruption.
2. Trigger a long Fish Audio spoken response. Observe `SPEAKING` on the screen.
3. During TTS, stay silent. TTS must not trigger `DETECTED`.
4. Make Fish Audio explicitly speak the phrase "Hey Muse" in its reply while nobody else speaks. It **must not** show `DETECTED`.
5. While TTS plays, have one person and then a different person say "Hey Muse". It **should** show `DETECTED` for 3 seconds while TTS continues.
6. Repeat at low and high speaker volume, different person-to-device distances, and while speaking over the TTS phrase.
7. Use ESP32 serial output tagged `tts_aec_test` for diagnostics and report false positives, missed detections and playback glitches.

## Important limitations

The speaker reference is captured at the codec write call, but speaker-to-mic acoustic propagation and I2S DMA latency **have not been calibrated**. AEC therefore may not reject the speaker's voice reliably. The current worker uses best-effort, chunk-queued reference data; a missing reference causes the associated wake check to be skipped (not treated as clean input). Neither a successful build nor a `DETECTED` indicator proves self-voice suppression.

The AEC worker can also introduce CPU, PSRAM, and mic/I2S contention. Unexpected audio glitches, freezes, or lost Wi-Fi would mean this experiment needs redesign before using it for hands-free barge-in.

The standard board's wake detector is still used; no new wake-word model or Pi software is required.

Reference: https://docs.espressif.com/projects/esp-sr/en/latest/esp32s3/acoustic_echo_cancellation/README.html
