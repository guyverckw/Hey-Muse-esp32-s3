# Phase 7a — Increase Hey Muse wake-word sensitivity

**Status:** prepared in GitHub, **not built, flashed, or hardware-accepted yet**.

## User-reported issue
Existing offline "Hey Muse" wake detection works, but usually fails on the first spoken attempt, requiring multiple repetitions. User explicitly wants to improve **existing** wake recognition before other voice-interaction work. Do not reimplement wake-word support or duplicate Muse cloud memory features.

## Code review and finding
The current local ESP32 model and inference path live in `esp32/components/muse/muse_wake.cpp`. It applies a rolling mean of six uint8 wake probabilities and requires that mean to exceed a 99%-of-255 threshold (`0.99f * 255.0f`, integer 252). That exceptionally strict cutoff is a plausible cause of missed real wake phrases. The wake input is captured every 20ms by `muse_voice.c`. The source also configures a microWakeWord 40-bin audio front-end and a 20-window warmup after resets. We **have not measured** whether microphone gain, room noise, placement, accent, or detector model itself are additional causes.

## Small initial change
- Wake score cutoff: **99% → 90%** (nominal: uint8 252 → 229).
- Keep six-result rolling average, warmup, audio frontend, microphone gain, model, routing, and all Pi code unchanged.
- Do not adjust gain and threshold simultaneously; isolate the effect and measure false triggers.
- Existing hardware baseline is safe in `stable/hey-muse-2026-11-21-tested` and user also saved full ESP32 flash / Pi backups prior to this change.

## Mac checks (before flashing)
```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
git status --short
git fetch origin
git switch --track origin/feature/phase7-wake-sensitivity-2026-11
python3 -m unittest esp32/tests/test_wake_sensitivity.py
c++ -std=c++17 -Wall -Wextra -Werror esp32/tests/test_tts_chunk.cpp -o /tmp/hey_muse_tts_chunk_test
/tmp/hey_muse_tts_chunk_test
. ~/esp/esp-idf-v6/export.sh
cd esp32
tools/muse/board.sh build s3n
```

If branch already exists locally, use `git switch feature/phase7-wake-sensitivity-2026-11` and `git pull --ff-only`; preserve uncommitted work. Once build passes, if ready to test on the board:
```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3/esp32
tools/muse/board.sh flash s3n
```

## Physical A/B acceptance plan

Keep same placement, mic gain, Wi-Fi, distance and room conditions. Record results, ideally against the known-good baseline if meaningful comparison is required.

1. From about 0.5–1m, say "Hey Muse" naturally **10 times**, only one attempt per trial (wait for prior reply to finish and detector to re-arm). Record number triggering on first try.
2. Repeat 10 times at 2–3m, same volume.
3. Leave the board listening for 10 minutes during normal conversation, music or TV, and count **false activations**.
4. Verify wake while screen is asleep and no unexpected microphone clipping or missed responses.
5. Confirm after waking: LISTENING → THINKING → SPEAKING → READY; long Fish Audio reply, Pi e-paper and 30s cooldown unchanged.

**Trade-off:** a less strict cutoff increases sensitivity but can also increase false positives. If false activations increase unacceptably, restore the stable branch / firmware backup, or retune with data. This test is pending; don't claim 90% is ideal before measuring.

## Notes
- The Pi is unaffected by this change.
- Never upload a private flash dump or tokens to GitHub.
- Keep this branch and PR separate from the accepted stable baseline.
