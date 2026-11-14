# Hey Muse — Recovery and Rebuild Guide

**Snapshot branch:** `backup/full-working-2026-11`
**Last documented:** 2026-11-14
**Status:** Sources were verified in GitHub; a clean-device restore has **not** yet been tested. Do not erase or overwrite either working device as part of this guide.

This guide documents the tested hardware arrangement and the version-controlled application sources for the ESP32-S3 Hey Muse companion and Raspberry Pi 3B display bridge. Keep the existing working installations intact while validating a fresh checkout.

## 1. Repository layout and what's backed up

- `esp32/`: Hey Muse ESP-IDF firmware, avatar-related source, and the reply/status bridge (`components/muse/muse_pi_bridge.cpp/.h`).
- `raspberry-pi/muse_pi.py`: Pi HTTP receiver, live OLED status, e-paper formatting and page navigation.
- `raspberry-pi/waveshare_epd/`: locally used 5.83-inch three-colour e-paper driver files and GPIO backend.
- `raspberry-pi/tests/`: four hardware test programs.
- `raspberry-pi/installers/`: historical change scripts; **not** required to reapply to the already-patched `muse_pi.py`.
- `raspberry-pi/legacy/`: earlier Phase 1 reference program.

The code on this branch reflects the files copied/committed in November 2026, not necessarily every subsequent live-device modification. Before recovery, compare the live devices' local Git status and source hashes. The Pi snapshot has `MIN_REFRESH_SECONDS = 180`; a previously discussed 30-second setting was **not** in the committed Pi file.

**Not included by design:** Wi-Fi passwords, Muse account/SDK token, Fish Audio credentials, bridge bearer token, ESP32 `muse_pi_bridge_config.h`, stored replies, generated previews, runtime refresh state, firmware build outputs, Python environments, and local experiments excluded from the snapshot.

## 2. Hardware and wiring

Known working Raspberry Pi 3B wiring uses BCM GPIO numbering (not physical header-pin numbering):

| Component | Bus / BCM pins |
| --- | --- |
| SH1106 128×64 OLED | SPI0 CE0; DC=24; RST=25; rotated 180° |
| Waveshare 5.83-inch (C) v1 e-paper | SPI0 CE1; DC=22; RST=17; BUSY=27; PWR=18; rotated 180° |
| Shared SPI | MOSI=10, SCLK=11 |
| Joystick | UP=6, DOWN=19, LEFT=5, RIGHT=26, SELECT=13 |
| Keys | KEY1=21, KEY2=20, KEY3=16 |

The active `epdconfig.py` is included in the repository. Both displays share SPI0 but use separate chip selects; do **not** run a second display test concurrently with the live `muse_pi.py` process (GPIO may already be claimed).

ESP32: Waveshare ESP32-S3-Touch-AMOLED-1.75 family, previously built using the `s3n` profile. Check your physical board label against the profiles in `esp32/tools/muse/board.sh` before flashing.

## 3. Recover the Raspberry Pi software (non-destructive staging)

On a replacement Pi with Raspberry Pi OS, enable SPI in Raspberry Pi configuration and reboot. For a **first-time staging checkout**, choose a separate folder from the live `~/hey-muse-display`:

```bash
git clone --branch backup/full-working-2026-11 \
  https://github.com/guyverckw/Hey-Muse-esp32-s3.git \
  ~/hey-muse-recovery
cd ~/hey-muse-recovery/raspberry-pi
python3 -m py_compile muse_pi.py
```

For a new system, the Python imports require at least: Pillow (`PIL`), `gpiozero`, `spidev`, `luma.core`, `luma.oled`, and the GPIO provider required by the platform. `fc-match` (fontconfig) and Noto CJK fonts support multilingual output. A starting point on Raspberry Pi OS is:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-pil python3-gpiozero python3-spidev fontconfig fonts-noto-cjk
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install luma.oled
```

Package names and GPIO driver compatibility depend on Raspberry Pi OS release; verify them on the target OS rather than treating this as a fully tested lockfile. If using a separate environment, ensure `spidev` and `gpiozero` can import there.

**Safe test without GPIO or e-paper wear:**

```bash
cd ~/hey-muse-recovery/raspberry-pi
python muse_pi.py --preview
```

This writes preview PNGs in the program's configured project directory. It should not initialise physical display hardware.

**To run the actual device on a fresh Pi only**, ensure the Waveshare drivers are importable beside `muse_pi.py`, and that you are not concurrently running another GPIO owner. The historically tested live command was:

```bash
python muse_pi.py --listen 0.0.0.0 --port 8765
```

`--listen 0.0.0.0` accepts connections from the LAN: use only on a trusted, firewalled network. No systemd auto-start has been confirmed by this snapshot. For a production restoration, deploy a service only after manual startup passes.

If this is the **same** existing Pi rather than a replacement, do not install packages or replace its source unnecessarily; verify it with `python3 -m py_compile`, `ps -eo pid,args | grep '[m]use_pi.py'`, and the health check below.

## 4. Recover private configuration — never put secrets in Git

The Pi bridge uses an authentication token:

- Local file: `~/.config/hey-muse-pi/bridge_token`, or a `MUSE_PI_TOKEN` environment override (minimum 24 characters).
- A fresh Pi run creates a new random token if neither is present. Keep file permissions restricted (`chmod 600`).
- The ESP32 requires a private **untracked** header at `esp32/components/muse/muse_pi_bridge_config.h` with macros `MUSE_PI_BRIDGE_URL` (including `/api/v1/reply`) and `MUSE_PI_BRIDGE_TOKEN` (matching the Pi token).
- Recreate this header from a securely held local copy, or make a new token on **both** devices. Do not commit, paste into chats, log, or include real secrets in screenshots.
- Keep other Muse/Fish Audio and Wi-Fi credentials in their intended secure local provisioning paths; follow the upstream firmware configuration notes. Do not assume a Git checkout alone will build or pair successfully.

The ESP32 URL must point to the actual Pi LAN address. A historical Pi address was `192.168.76.164`; do not assume it remains current.

## 5. Recover ESP32 firmware (build before flashing)

On macOS, install/activate **ESP-IDF v6.0.1**, previously at `~/esp/esp-idf-v6`. See `esp32/README.md` and `esp32/AGENTS.md` for full SDK prerequisites and Muse pairing.

```bash
cd ~/hey-muse-recovery/esp32  # adjust to the local checkout on your Mac
. ~/esp/esp-idf-v6/export.sh
tools/muse/board.sh build s3n
```

The exact `s3n` mapping is declared in `board.sh`; confirm the board model and provisioning before using it. The build tool writes `/tmp/muse_build_s3n.log`. It deletes/rebuilds managed components, so avoid simultaneous builds on different profiles.

**Flashing is a separate, optional, higher-risk step.** Only on a board you intend to reflash, after checking port and configuration:

```bash
ls /dev/cu.usb*
tools/muse/board.sh flash s3n /dev/cu.usbmodemYOURPORT
```

Replace the placeholder with the device's current real port. Do **not** erase flash on your working device or expose SDK tokens while troubleshooting.

## 6. Verify the Pi → ESP32 connection

On the Pi (or another device that can reach the Pi):

```bash
curl http://127.0.0.1:8765/health
```

Expected JSON has `"status":"ok"` and `"service":"hey-muse-pi-bridge"`. This proves only that the Pi HTTP service is up.

The ESP32 sends authenticated JSON via:

- `POST /api/v1/reply` — `{"text":"...", "source":"esp32"}`
- `POST /api/v1/status` — `{"state":"listening"|"thinking"|"speaking"|"idle"|"error"}`

Successful calls return HTTP 202. Watch Pi OLED for LISTENING → THINKING → SPEAKING → READY, and e-paper for replies. The current Pi software imposes a 180-second e-paper refresh cooldown. Do not repeatedly run e-paper hardware tests to speed up diagnosis; the 5.83-inch three-colour panel has hardware refresh limitations.

At the time of this snapshot, `muse_pi_bridge.cpp` limits forwarded reply text to **1023 bytes** (`strnlen`); long Chinese/Japanese responses may be truncated, potentially within a UTF-8 character. This remains future work, not a resolved backup feature.

## 7. Buttons, page navigation and current limitations

- UP/DOWN: OLED menu selection
- SELECT: execute menu selection
- LEFT/RIGHT: previous/next response page
- KEY2: latest reply/page 1 (subject to cooldown)
- KEY3: previous page
- KEY1: reset menu selection to the first item

Response text uses a compact, approximately 17-line layout at 600×448 pixels with 18-pixel body type, and supports tested English, Traditional Chinese, Simplified Chinese and Japanese samples. Exact lines/page vary with text and wrapping. For nonresponse screens a smaller title/accent remains.

## 8. Integrity, backups and next steps

On the **existing working** Pi and the corresponding checkout, compare:

```bash
sha256sum ~/hey-muse-display/muse_pi.py \
  ~/hey-muse-github-backup/raspberry-pi/muse_pi.py
```

Repeat for `waveshare_epd/*.py` and selected scripts. A GitHub commit records only copied files, not the installed operating system, system packages, current credentials, live conversations, or unsaved local changes.

Recovery checklist:

- [ ] Checkout the correct snapshot branch on a separate directory
- [ ] Verify source hashes against the desired working version
- [ ] Enable SPI and confirm wiring/power
- [ ] Install/verify Python dependencies and multilingual fonts
- [ ] Restore private bridge/SDK credentials outside Git
- [ ] Run GPIO-free preview and syntax checks
- [ ] Start exactly one Pi display service and test `/health`
- [ ] Build ESP-IDF firmware; flash **only if recovery requires it**
- [ ] Confirm wake word, multilingual conversation, OLED status, and e-paper
- [ ] Document any differences discovered in a real clean restore

For code changes, work on a feature branch and review diffs before merging or flashing. Keep the working backup branch as a known reference until a later version is tested on both devices.
