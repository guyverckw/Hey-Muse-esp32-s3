# Pi-only OLED SPEAKING lifetime fix

The user confirmed that the ESP32 full-length Fish Audio response is spoken to completion and the Raspberry Pi receives the full answer. The OLED prematurely displays READY after approximately 90 seconds even when voice playback continues.

## Root cause
The Pi runs a 90-second stale-status timeout for every non-idle status. The existing ESP32 firmware sends SPEAKING at audio playback start, and sends IDLE when playback finishes, with no heartbeat between these events.

## Pi-only remedy
- Keep original 90-second stale fallback for LISTENING, THINKING and ERROR.
- Allow SPEAKING up to 15 minutes as a stale-status fail-safe. This exceeds the current ESP32 long-speech cap (12 minutes).
- An actual status packet, particularly IDLE, **always takes priority**: READY appears immediately once the Pi receives IDLE.
- Does not alter the Raspberry Pi e-paper configuration, systemd service, Fish Audio, networking, or ESP32 firmware.
- Does not guarantee READY exactly at the audible final sample; it relies on the ESP32 sending its existing IDLE event after the playback loop. Network delay can add a brief delay.
- On ESP32 crash, lost IDLE, or network outage while SPEAKING, the OLED may remain SPEAKING for up to 15 minutes; this is a trade-off of avoiding ESP32 changes.

**Branch:** `feature/pi-speaking-status-lifetime-2026-11`, based on corrected Phase 6b Pi version. The previously working long-speech ESP32 firmware stays installed.

## Validate without touching live Pi code

On Raspberry Pi:

```bash
cd ~/hey-muse-github-backup
git fetch origin
git switch --track origin/feature/pi-speaking-status-lifetime-2026-11
cd raspberry-pi
python3 -m py_compile muse_pi.py
python3 -m unittest discover -s tests -p 'test_speaking_timeout.py'
python3 -m unittest discover -s tests -p 'test_network_menu.py'
python3 -m unittest discover -s tests -p 'test_oled_status.py'
python3 -m unittest discover -s tests -p 'test_single_instance.py'
python3 -m unittest discover -s tests -p 'test_pagination.py'
```

If local Git branch already exists, use `git switch feature/pi-speaking-status-lifetime-2026-11` and `git pull --ff-only`. Preserve any local edits first.

## Deploy only after all tests pass

```bash
cd ~/hey-muse-display
cp -p muse_pi.py "muse_pi.before_speaking_fix_$(date +%Y%m%d_%H%M%S).py"
# Ensure no e-paper refresh is running.
sudo systemctl stop hey-muse-pi.service
cp ~/hey-muse-github-backup/raspberry-pi/muse_pi.py ~/hey-muse-display/muse_pi.py
python3 -m py_compile ~/hey-muse-display/muse_pi.py
sudo systemctl start hey-muse-pi.service
systemctl is-active hey-muse-pi.service
systemctl show hey-muse-pi.service -p Environment -p MainPID -p NRestarts
curl -fsS http://127.0.0.1:8765/health
```

Expected environment still includes `MUSE_EPAPER_REFRESH_SECONDS=30` if the previously requested Pi systemd override has been installed successfully. The Python patch does not set the cooldown itself.

## Physical tests (pending)
- [ ] Pi tests pass
- [ ] Service stable with no unexpected restart
- [ ] Short voice: LISTENING → THINKING → SPEAKING → READY
- [ ] Long voice (>90 seconds): SPEAKING remains active throughout; READY arrives after final audio
- [ ] Pi e-paper pagination and preferred cooldown unaffected
- [ ] If ESP32 disconnects during SPEAKING, no premature READY; 15-minute stale fallback (may simulate by manipulating status in a standalone test rather than waiting on real hardware).

For rollback, stop service, restore the newest `muse_pi.before_speaking_fix_*.py` to `muse_pi.py`, and start service. The separate ESP32 heartbeat PR #5 is an alternative but **not required** for this Pi-only solution; don't flash it.

## Raspberry Pi development checkout validation — 2026-11-21

User fetched branch `feature/pi-speaking-status-lifetime-2026-11`, successfully switched to tracking its origin, and executed the Pi tests:

- `python3 -m py_compile muse_pi.py` — **PASS** (no errors)
- `test_speaking_timeout.py` — **3/3 PASS**
- `test_network_menu.py` — **5/5 PASS**
- `test_oled_status.py` — **5/5 PASS**
- `test_single_instance.py` — **2/2 PASS**
- `test_pagination.py` — **3/3 PASS**

**Total: 18/18 PASS.** This establishes static/software test success, **not** physical OLED acceptance. Live Pi deployment and a long spoken-response test remain pending. No ESP32 firmware changes are required.

## Physical test regression — 2026-11-21

User reported after proceeding with the Pi-only fix: **"The OLED doesn't work, it didn't change states, just keep showing READY and the icons didn't change at all."** This is not the initial bug (SPEAKING reverting to READY after 90 seconds), because no transient status is displayed at all. The source diff is limited to per-state timeout logic, so the causal explanation is **unconfirmed**. Possible causes include ESP32-to-Pi status messages not reaching the bridge, wrong live file/version, or Pi queue/render path not processing status. Do not mark fix complete.

**Next diagnostics:** check systemd service health/restarts, authenticated `POST /api/v1/status` HTTP response codes from the Pi journal during an ESP32 interaction, and which `muse_pi.py` is actually running. Collect journal entries before rollback. Restore latest known-good `muse_pi.before_speaking_fix_*.py` backup if live functionality is impaired, without modifying ESP32 firmware or the 30-second systemd cooldown drop-in.
