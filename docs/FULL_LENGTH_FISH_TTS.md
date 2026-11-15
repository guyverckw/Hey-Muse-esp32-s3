# Full-length Fish Audio TTS — Phase 6c firmware development

**Status: GitHub development only — NOT BUILT, FLASHED OR PHYSICALLY TESTED.**

## Version and boundaries

- Branch: `feature/full-length-fish-tts-2026-11`
- Recovery base branch: `backup/phase6b-pi-stable-2026-11`
- Verified earlier ESP32 firmware: the user's currently installed and working Muse/Fish Audio firmware, which must not be overwritten without a successful build and backups
- **No Raspberry Pi Python/service/e-paper code changes** in this feature
- Pi e-paper cooldown remains 180 seconds

## Root cause and new implementation

The existing `muse_chat_session.cpp` forwards up to 8,192 UTF-8 bytes to the Pi but supplies only the earlier 1,024-byte caption buffer to Fish Audio. Previously a multi-page answer could reach e-paper while speech stopped after a small portion of the reply.

This increment:

1. Uses the independent `msg_t.pi_full` reply buffer as Fish Audio's input, falling back to the original caption buffer only if the full buffer is unavailable.
2. Splits it into **sequential requests of at most 700 UTF-8 bytes**. Splits preserve every byte, never cut a UTF-8 continuation byte, and prefer nearby punctuation/whitespace for natural pauses.
3. Waits for each Fish Audio generation to finish before starting the next, sending its PCM into the existing voice queue with the original generation/cancellation guard. On failure, stops subsequent chunks instead of silently skipping text or speaking out of order.
4. Extends the maximum voice-turn allowance from 180 seconds to **12 minutes only for turns with active/completed speech**, while keeping the ordinary cap for voice turns without generated speech.
5. Does not increase the 1 KB OLED caption representation, so captions on the ESP32 can remain truncated even when the longer reply is fully spoken and displayed on Pi.
6. Does not increase the 8,192-byte Pi reply cap. Text beyond that bound is still clipped (and a warning is logged). For the previously tested ~3.3 KB reply, speech should be able to cover the complete captured text, subject to successful Fish API calls and playback.

This uses **multiple Fish Audio requests per reply**, which may increase API usage, charges, latency and network activity. Do not repeatedly run lengthy TTS tests without monitoring usage. Each request's content goes to the already configured Fish Audio service under the user's existing API key.

## Step 1 — Mac checkout and pure C++ chunking tests

On the Mac (repository clone):

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
git status --short
git fetch origin
git switch --track origin/feature/full-length-fish-tts-2026-11
c++ -std=c++17 -Wall -Wextra -Werror \
  esp32/tests/test_tts_chunk.cpp -o /tmp/hey_muse_tts_chunk_test
/tmp/hey_muse_tts_chunk_test
```

If already on the feature branch, use `git switch feature/full-length-fish-tts-2026-11` followed by `git pull --ff-only`. If the checkout contains local/uncommitted changes, do not discard them; back them up or use a separate Git worktree first.

Expected: `PASS: lossless UTF-8 chunking, sizes, order and boundaries`.

## Step 2 — Compile ESP32 firmware only

With the usual Muse ESP-IDF development environment configured:

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
. ~/esp/esp-idf-v6/export.sh
cd esp32
tools/muse/board.sh build s3n
```

Use the actual ESP-IDF export path if it differs on the Mac. The build must pass without warnings/errors from the new code before flashing. Keep the previously working binary and local settings backed up.

**Build script location:** `esp32/tools/muse/board.sh`. From the repository root, `tools/muse/board.sh` does not exist. The script writes its build log to `/tmp/muse_build_s3n.log`.

## Step 3 — Physical regression after successful build (do not flash prematurely)

Only after reviewing the build result and identifying a working firmware recovery image:

```bash
tools/muse/board.sh flash s3n
```

The board name and flash invocation are those used previously on this user's ESP32-S3. Do not flash until a backup/recovery route is secured.

### Test cases after flashing

- Short one-sentence answer: speaks normally once, and Pi display still receives the reply.
- Multi-page ~3,000–4,000-byte answer: sequential logs `Fish Audio chunk 1`, `chunk 2`, ... and a final `Fish Audio completed ...`; **listen to ensure the entire answer is audible**, not merely that API requests returned OK.
- Chinese/multilingual answer: chunking does not garble UTF-8 characters.
- New/cancelled turn during playback: cancellation stops the old audio and doesn't bleed into the next reply.
- Existing OLED animations, network signal, e-paper page queue and Pi 180-second refresh remain functional.
- No unexpected ESP32 reboots, memory allocation failures or network disconnects.

**Do not copy API keys or authenticated HTTP headers into GitHub or chat.** Prefer redacted logs showing chunk counts, errors and service status.

## Risks / acceptance still pending

- [ ] Native chunk test compiled and passed on Mac
- [ ] ESP-IDF firmware compiled successfully
- [ ] Tested short speech
- [ ] Tested full ~3 KB speech audibly to the end
- [ ] Verified Pi continues to receive and display the full reply
- [ ] Verified interrupt/cancellation and no unexpected resets
- [ ] Confirmed acceptable Fish Audio latency and API usage

If long speeches fail even with chunked text, investigate Fish Audio's per-request behaviour, PCM queue backpressure, turn-lifetime and ESP32 serial logs before increasing buffer sizes or changing Pi code.

## Mac build result — 2026-11-15 (user-reported)

User compiled and ran the standalone C++ UTF-8 chunk test on the Mac:

```
PASS: lossless UTF-8 chunking, sizes, order and boundaries
```

The first firmware build command (`tools/muse/board.sh build s3n` from repository root) did not execute because the script is under `esp32/tools/muse/board.sh`. After `cd esp32`, the user ran `tools/muse/board.sh build s3n` and received the successful ESP-IDF build trailer containing the exact generated `esptool ... write-flash` command for `build-muse-waveshare-s3-175/muse-gadget.bin`. This indicates **BUILD PASSED**; the output is a build instruction, not evidence of flashing.

- [x] Native C++ UTF-8 chunk test **PASS**
- [x] ESP-IDF 6.0 build for s3n **PASS**, based on user's final build output
- [ ] Full flash backup / tested firmware recovery artifact securely saved locally
- [ ] Flash new build on ESP32
- [ ] Test short speech, audible complete multi-page speech and cancellation

**Do not commit a flash dump to GitHub:** it can contain tokens, passwords and paired-device secrets.

## Verified firmware backup — 2026-11-15

User successfully completed a **full ESP32-S3 flash read** before attempting the new TTS firmware:

- Board detected over `/dev/cu.usbmodem14201`, ESP32-S3 revision v0.2, 8 MB embedded PSRAM, 16 MB flash.
- `python -m esptool --chip esp32s3 -p "$PORT" -b 460800 read-flash 0 ALL ...` finished without errors.
- Exact read: **16,777,216 bytes** from flash offset `0x00000000`.
- Private local recovery image: `~/Documents/ESP32/MUSE/firmware-backups/hey-muse-before-long-tts.bin`.
- User ran `shasum -a 256`; SHA-256 recorded locally as `30ecd38ccc8870a70032a1bc49c7c48dde555cbd4cc35720ba422edf01b4366e`. Never commit the flash image or credentials.
- **Backup passed; new firmware not yet flashed or hardware tested.**

### Restore reference (only if needed)

With the device port detected and confirmed as the intended board, run from the Mac's `esp32` directory:

```bash
PORT="$(python tools/muse/ports.py s3n)"
python -m esptool --chip esp32s3 -p "$PORT" -b 460800 \
  write-flash 0x0 ~/Documents/ESP32/MUSE/firmware-backups/hey-muse-before-long-tts.bin
```

This writes the complete original flash image, including credentials and provisioning data, to **the same board**. Do not run unless recovering. It will overwrite the firmware currently installed.

## Flash and short-speech physical test — 2026-11-15

User ran `tools/muse/board.sh flash s3n` on the Mac. The output ended in `Hash of data verified.` followed by `Hard resetting via RTS pin...`, indicating a successful flash operation. The user explicitly confirmed **short voice test passes**.

- [x] Full 16 MB previous firmware backup obtained privately (previous section)
- [x] Flashing of feature firmware on ESP32-S3 **PASS**
- [x] Short Fish Audio voice response **PASS (user-confirmed)**
- [ ] Long (~500-word) response spoken fully to final sentence
- [ ] Check no missing/reordered chunks and no unexpected resets
- [ ] Check full reply forwarding and Pi multi-page e-paper navigation

**Do not mark the full-length TTS feature complete until the user confirms long-response physical playback.**
