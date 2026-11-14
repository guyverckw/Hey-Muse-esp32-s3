# Phase 4c — Long UTF-8 AI replies to Raspberry Pi

**Status: Source prepared on a development branch; build, flashing, and physical tests not yet performed.**

Branch: `feature/phase4c-long-replies-2026-11`. Previous working snapshot: `backup/full-working-2026-11`. Phase 4b validated branch: `feature/epaper-queued-pagination-2026-11`.

## Why the change was necessary

The original ESP32 Pi bridge stopped at 1,023 bytes, and `muse_chat_session.cpp` retained just 1,024 bytes per message for captions and Fish Audio TTS. Increasing only the HTTP limit would **not** recover longer replies if the streamed message had already been truncated before reaching the bridge.

The new code stores a separate UTF-8 string for each streamed assistant message, capped at **8,192 bytes**, and prefers the complete `display_text`/`content` supplied by Muse at message completion when available. A separate buffer is allocated lazily, per message, and reclaimed when a new turn starts. The existing 1,024-byte Fish Audio/caption buffer is *unchanged* to avoid destabilising established speech timing. Neither the Pi protocol nor its authentication changes.

**Limitation:** 8,192 bytes is a bound, not unlimited replies. Larger messages will be truncated at a UTF-8 character boundary. Fish Audio speech still uses the prior short caption buffer and may **not speak the entire long answer**. The goal of this phase is complete *e-paper forwarding up to 8 KiB* while preserving previously working TTS behaviour.

## Step 1 — Mac: fetch and build, without disturbing the working firmware

In a MacBook Terminal:

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
git fetch origin
git status --short
git switch --track origin/feature/phase4c-long-replies-2026-11
. ~/esp/esp-idf-v6/export.sh
tools/muse/board.sh build s3n
echo "build exit=$?"
tail -n 45 /tmp/muse_build_s3n.log
```

If the branch already exists, run `git switch feature/phase4c-long-replies-2026-11` and `git pull --ff-only`. Do not use `git reset --hard`, `git clean -fd`, or stage untracked private configuration files. `board.sh` clears managed components while building, so avoid simultaneous board builds.

**If compile fails, do not flash.** Send the compiler errors (remove any secrets or tokens first).

## Step 2 — Optional: verify the running Pi without changing it

Pi Phase 4b must be running and `/health` responding on port 8765. The full-reply limit on Pi is `MAX_REPLY_CHARS = 12000`, and HTTP requests are bounded by `MAX_POST_BYTES = 32768`; 8 KiB of unescaped UTF-8 fits.

```bash
curl http://127.0.0.1:8765/health
```

Do not launch another display-owning Python process while the live Pi service is running.

## Step 3 — Flash only after a successful build (manual hardware test)

Save your current working build/branch and configuration before flashing. Ensure the private, Git-ignored `esp32/components/muse/muse_pi_bridge_config.h` still exists locally and contains the correct **private** Pi URL and Bearer token. Never print its contents in chat.

Find the current USB port:

```bash
ls /dev/cu.usb*
```

Then, if ready to update the physical ESP32 (replace the placeholder with your actual USB device):

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3/esp32
tools/muse/board.sh flash s3n /dev/cu.usbmodemYOURPORT
```

Note: `board.sh` is run **inside** `esp32/`. Verify the board is the 1.75-inch `s3n` target in your setup. A flash changes running firmware; GitHub branch creation does not.

## Step 4 — Ask Hey Muse for a long answer

1. Request an English explanation of 400–600 words, or a long Traditional Chinese / Simplified Chinese / Japanese response.
2. Confirm the OLED transitions LISTENING → THINKING → SPEAKING → READY.
3. Confirm the latest Pi reply contains more than 1,023 UTF-8 bytes and that e-paper shows page `1/N` with `N > 1`.
4. Use RIGHT and LEFT to inspect pages. Press RIGHT twice during cooldown; the latest requested page should remain queued.
5. Compare the Pi's received text with the AI response where possible. Test multibyte characters near the length limit to catch broken glyphs.
6. Confirm Fish Audio still produces speech; it is not expected to speak every byte of an 8-KiB answer in this release.
7. Note any ESP32 warnings about a reply exceeding 8,192 bytes, or memory allocation errors.

On the Pi, you can measure the length of only the **latest** stored reply without displaying private conversation content. First confirm the local source stores `conversation_history.jsonl` in `~/hey-muse-display`:

```bash
python3 - <<'PY'
from pathlib import Path
import json
p = Path.home() / "hey-muse-display/conversation_history.jsonl"
if not p.exists():
    raise SystemExit("No reply history found")
last = json.loads(p.read_text(encoding="utf-8").splitlines()[-1])
text = last.get("text", "")
print("Source:", last.get("source", "unknown"))
print("UTF-8 bytes:", len(text.encode("utf-8")))
print("Unicode characters:", len(text))
PY
```

Do not paste or commit the actual conversation history.

## Rollback

Keep `backup/full-working-2026-11` and the proven Phase 4b Pi code available. If the new firmware causes any wake-word, speech or networking regression, return to the previous ESP32 firmware build and flash it deliberately using the previous working source, after preserving diagnostics. Do not overwrite the Pi program or its conversation history.

## Acceptance criteria

- [ ] ESP-IDF `s3n` build succeeds
- [ ] ESP32 boots, pairs and wake-word detection still works
- [ ] Fish Audio still speaks as before
- [ ] Pi receives an actual **ESP32-sourced** reply exceeding 1,023 bytes
- [ ] E-paper displays all received pages with valid English/CJK glyphs
- [ ] LEFT/RIGHT queued navigation still works
- [ ] OLED live-status transitions still work
- [ ] No token or credential is committed

## Regression found during first physical test

The first user-reported long-answer test on 2026-11-14 returned exactly **1,023 UTF-8 bytes** / 1,017 characters from source `esp32`. The reply was incomplete. The earlier patch changed the HTTP bridge limit but **missed the voice-specific fallback** within `message_done()`, which could still send the short 1,024-byte caption text buffer. The final event field could also be shorter than accumulated streamed content.

Follow-up fix commits `aee058d` and `092b856` now select the longer available representation for the Pi in **both** voice and text turns, and log only byte lengths (no private message text). A **new firmware build and flash** are required; the earlier successfully built and flashed firmware does not contain these corrections.

After flashing the corrected build, for a real voice interaction inspect serial messages:
- `Pi reply bytes stream=... final=... selected=... (cap=8192)`
- `Pi reply queued: ... UTF-8 bytes`
- `Reply delivered to Raspberry Pi (202)` or a relevant HTTP error

Compare the selected and queued byte counts with the most recent Pi history entry (check the **source is esp32**). Do not paste private reply content, credentials or tokens into diagnostics.

**Separate scope:** Fish Audio still reads from the 1 KiB speech buffer; spoken audio may stop early even when a full multi-page e-paper reply is delivered. Do not mark full-length TTS solved by this fix. If the **server itself** terminates generation early, that is a separate issue from the Pi forwarding limit.

## Follow-up Pi result — 2026-11-14

After the corrected firmware rebuild/reflash sequence, user reported the latest saved Pi message as:

- Source: `esp32`
- UTF-8 bytes: **3,327** (previous failed test: **1,023**)
- Unicode characters: **3,305** (previous: **1,017**)

**Result:** ESP32-to-Pi forwarding of a message longer than the prior 1,023-byte limit is confirmed by Pi history. Still pending: confirmation the message ends naturally without truncation, live wake-word/Fish Audio/OLED regression results, and full multi-page navigation with the new real reply. The existing TTS 1 KiB buffer is unchanged.
