# Hey Muse stable baseline — hardware-accepted 2026-11-21

**Baseline branch:** `stable/hey-muse-2026-11-21-tested`

**Acceptance:** The user confirmed an approximately 500-word spoken answer completed successfully, with full response displayed on the Raspberry Pi e-paper and appropriate OLED states after restoring ESP32↔Pi Wi-Fi connectivity.

## What's in this GitHub baseline

The baseline deliberately combines two previously separate **user-tested** code paths:

| Component | Verified source | What this baseline contains |
| --- | --- | --- |
| ESP32-S3 firmware | `feature/full-length-fish-tts-2026-11` | Fish Audio full reply spoken in sequential UTF-8-safe chunks up to the existing 8 KB captured reply; no extra ESP32 status-heartbeat change |
| Raspberry Pi | `feature/pi-speaking-status-lifetime-2026-11` | OLED SPEAKING persists past 90 seconds, with a 15-minute stale-message fallback and explicit IDLE switching to READY; network/menu/status and e-paper pagination remain |
| Pi systemd configuration | user's live Pi service drop-in | User-configured e-paper cooldown of **30 seconds**; override is stored on the Pi, **not automatically recreated by checking out this Git branch** |

All original device source settings and any stored credentials are kept outside these new baseline documents. Do not commit Pi token files, Wi-Fi passwords, Fish Audio API keys, or binary flash dumps.

## How the accepted configuration was verified

- ESP32 native UTF-8 text chunk test passed on Mac.
- ESP-IDF s3n firmware built and was successfully flashed; esptool reported hash verification.
- A complete 16 MB **pre-long-TTS** ESP32 flash backup was created locally before flashing (not in GitHub).
- User confirmed short voice playback and full-length Fish Audio speech.
- Pi regression suites (3 + 5 + 5 + 2 + 3) all passed: **18 tests** plus Python compilation.
- User confirmed long e-paper text and 30-second systemd cooldown override.
- When the OLED was stuck READY, the cause was ESP32 connected to a different Wi-Fi network; after reconnecting to the intended network, OLED states worked.
- Final ~500-word spoken response: **user confirmed everything working fine**, including long-speech OLED transition behaviour.

**Important:** The combined baseline branch is a repository composition of these individually tested versions. There was no separate new firmware/Pi flash or end-to-end retest of this newly assembled Git branch. Its key executable source files were copied byte-for-byte from the successful development branches.

## Persistent 30-second Pi e-paper cooldown

The default tracked unit (`raspberry-pi/systemd/hey-muse-pi.service`) still specifies 180 seconds. The user's live unit was configured using a **systemd drop-in**, to retain 30 seconds through reboot. On a restored/new Pi, install the following:

```bash
sudo mkdir -p /etc/systemd/system/hey-muse-pi.service.d
printf '[Service]\nEnvironment=MUSE_EPAPER_REFRESH_SECONDS=30\n' | \
  sudo tee /etc/systemd/system/hey-muse-pi.service.d/refresh.conf
sudo systemctl daemon-reload
# Only restart when the e-paper is idle:
sudo systemctl restart hey-muse-pi.service
systemctl show hey-muse-pi.service -p Environment
```

The expected environment includes `MUSE_EPAPER_REFRESH_SECONDS=30`. The panel previously took roughly 47 seconds per full update; **30 seconds is the minimum interval between refresh starts, not a guaranteed completed page every 30 seconds**. Frequent tri-colour full refreshes may shorten the panel's service life.

## Pi deployment or recovery

On a Pi clone, fetch and select the stable branch:

```bash
cd ~/hey-muse-github-backup
git fetch origin
git switch --track origin/stable/hey-muse-2026-11-21-tested
cd raspberry-pi
python3 -m py_compile muse_pi.py
python3 -m unittest discover -s tests -p 'test_speaking_timeout.py'
python3 -m unittest discover -s tests -p 'test_network_menu.py'
python3 -m unittest discover -s tests -p 'test_oled_status.py'
python3 -m unittest discover -s tests -p 'test_single_instance.py'
python3 -m unittest discover -s tests -p 'test_pagination.py'
```

If already checked out, `git switch stable/hey-muse-2026-11-21-tested` then `git pull --ff-only`. Never discard local changes without a backup.

Only if redeployment is necessary, back up the working `~/hey-muse-display/muse_pi.py`, wait for the e-paper to be idle, stop `hey-muse-pi.service`, copy `raspberry-pi/muse_pi.py` into the live location, compile and restart. The live Pi is working already; **no current redeployment is needed**.

## ESP32 build and recovery

The `esp32` directory contains the board build script. From the Mac clone:

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
git fetch origin
git switch --track origin/stable/hey-muse-2026-11-21-tested
. ~/esp/esp-idf-v6/export.sh
cd esp32
tools/muse/board.sh build s3n
```

Do not reflash working hardware solely to create or use this Git baseline. If rebuilding in the future, create an additional **private local backup of the currently running successful long-TTS flash** first; the previously saved 16 MB file is from **before** the full-length TTS upgrade and is not a snapshot of the currently accepted firmware.

Keep the existing original 16 MB flash dump under the user's private Mac `firmware-backups` folder; don't upload it to GitHub. For rollback to that original state only, identify the correct board serial port and use esptool `write-flash 0x0 <private-backup.bin>`, understanding that this restores older firmware and NVS settings.

## Stable branch policy

Treat this branch as **read-only** after this document is committed. All subsequent features should branch from this tested snapshot rather than changing it. Keep the earlier experimental ESP32 heartbeat PR #5 unflashed and unmerged. Do not merge unfinished draft PRs into this baseline or `main` automatically.
