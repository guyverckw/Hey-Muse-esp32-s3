# Phase 6 — Enhanced OLED Status (first increment)

**Status: source changes committed on a separate development branch. Not installed or physically tested on the Pi.**

- Tested Phase 5 recovery branch: `backup/phase5-tested-2026-11`
- New development branch: `feature/phase6-oled-status-2026-11`
- Raspberry Pi service: `hey-muse-pi.service` (existing, unchanged)
- Live app: `/home/musepi/hey-muse-display/muse_pi.py`

## Scope of this increment

The OLED's top line now shows a small changing waveform while listening and speaking, animated dots while thinking, a static indicator while ready, and an exclamation mark for errors. The bottom line still prioritises active MUSE status; otherwise it can show `EPAPER Q 42s`, `EPAPER QUEUED`, `EPAPER UPDATING`, `NEW REPLY - KEY2` or `MUSE: READY`. The menu, reply page numbers, and physical button mappings are unchanged.

The OLED animation is driven by time in the *existing main thread*, approximately two frames per second. It never invokes an e-paper update or changes the persisted three-minute e-paper cooldown. No change to ESP32 firmware, authenticated HTTP, Fish Audio or Phase 5 systemd service.

**Not included yet:** signal-strength display or accurate network connectivity indication. Such a feature needs a reliable health probe and should not claim the ESP32 is online merely because the Pi Wi-Fi is associated.

## A. Run no-hardware tests without touching the running service

SSH into the Pi and run:

```bash
cd ~/hey-muse-github-backup
git fetch origin
git switch --track origin/feature/phase6-oled-status-2026-11
cd raspberry-pi
python3 -m py_compile muse_pi.py
python3 -m unittest discover -s tests -p 'test_oled_status.py'
python3 -m unittest discover -s tests -p 'test_single_instance.py'
python3 -m unittest discover -s tests -p 'test_pagination.py'
```

If the branch exists already, `git switch feature/phase6-oled-status-2026-11` followed by `git pull --ff-only`. These tests do not initialise GPIO or e-paper hardware. Do **not** start a second `muse_pi.py` hardware process while systemd owns the displays.

## B. Stage a rollback and update the working script

Only after tests pass, save the current Phase 5 live file:

```bash
cd ~/hey-muse-display
cp -p muse_pi.py "muse_pi.before_phase6_$(date +%Y%m%d_%H%M%S).py"
ls -lt muse_pi.before_phase6_*.py | head
```

Ensure the e-paper is not in the middle of a refresh; then stop the service gracefully, copy only the updated Python script, and start it again:

```bash
sudo systemctl stop hey-muse-pi.service
cp ~/hey-muse-github-backup/raspberry-pi/muse_pi.py ~/hey-muse-display/muse_pi.py
python3 -m py_compile ~/hey-muse-display/muse_pi.py
sudo systemctl start hey-muse-pi.service
```

The process retains its previous token, reply history, and hardware-specific Waveshare driver. The existing systemd unit remains enabled at boot. Normal operation requires **no terminal commands** after a reboot.

## C. Test the real OLED and companion

```bash
systemctl status hey-muse-pi.service --no-pager
curl -fsS http://127.0.0.1:8765/health
journalctl -u hey-muse-pi.service -n 35 --no-pager
```

On the actual OLED, confirm:

1. IDLE/READY is steady and the existing menu is legible.
2. Ask Hey Muse a short question: LISTENING, THINKING, SPEAKING have a small moving indicator at top right. OLED status words remain readable.
3. Page navigation with RIGHT/LEFT and e-paper cooldown still works as in Phase 5. Queued requests show `Q` in page line and a queue/cooldown message when Muse is idle.
4. All physical buttons still work and e-paper refresh remains independent of OLED animation.
5. Ask a longer question and confirm reply delivery, Fish Audio and multi-page e-paper remain functional.
6. Reboot when convenient; the unchanged Phase 5 systemd service must start the app automatically.

## Rollback — restores exact working Phase 5 app

If the OLED is unreadable, e-paper locks up, or the service fails:

```bash
sudo systemctl stop hey-muse-pi.service
cd ~/hey-muse-display
ls -lt muse_pi.before_phase6_*.py | head
cp -p muse_pi.before_phase6_YYYYMMDD_HHMMSS.py muse_pi.py
python3 -m py_compile muse_pi.py
sudo systemctl start hey-muse-pi.service
```

Replace the placeholder with the timestamp of the saved file. **Do not** delete `conversation_history.jsonl`, `refresh_state.json`, or the private token.

## Acceptance

- [ ] All three test suites pass on the Pi
- [ ] OLED animation states legible and responsive on real hardware
- [ ] Queue feedback and page numbers correct
- [ ] No regressions in e-paper, HTTP bridge, Fish Audio or GPIO
- [ ] Phase 5 service reboot and restart remain functional

## Phase 6 pre-deployment Raspberry Pi tests — 2026-11-15

User ran the no-hardware test suite on Raspberry Pi after switching to `feature/phase6-oled-status-2026-11`:

- `python3 -m py_compile muse_pi.py`: **PASS** (no errors)
- `test_oled_status.py`: **5 tests PASS**
- `test_single_instance.py`: **2 tests PASS**
- `test_pagination.py`: **3 tests PASS**

**Status: software tests PASS; physical deployment and OLED/e-paper regression tests not yet performed.** Preserve the working Phase 5 live script before copying the Phase 6 code. The existing systemd unit is unchanged.

## Physical OLED animation test — 2026-11-15

After the Phase 6 application deployment steps, the user reported: **"The OLED animations are working as expected."**

- [x] Pi software validation: five OLED-status, two singleton, three pagination tests passed
- [x] OLED animated status interface works on the actual display (user-reported): **PASS**
- [ ] Final end-to-end regression: verify a fresh ESP32-sourced reply, normal Fish Audio speech, e-paper display and physical LEFT/RIGHT navigation
- [ ] Confirm Phase 5 systemd service still starts correctly following reboot (optional final verification if service was not modified)

**Status:** Phase 6 OLED animation increment physically validated; complete phase acceptance pending final end-to-end check. No changes were made to the ESP32 firmware, e-paper driver or systemd unit.
