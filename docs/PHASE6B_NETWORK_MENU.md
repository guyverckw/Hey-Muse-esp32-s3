# Phase 6b — Local network indicators and OLED menu polish

**Status: code staged in GitHub only. No physical installation or tests yet.**

Base / recovery branch: `backup/phase6a-oled-tested-2026-11`
New branch: `feature/phase6b-network-menu-2026-11`
Current running systemd service: `hey-muse-pi.service` (no unit changes)

## New OLED indicators

- Top row **W**: Linux reports the Raspberry Pi Wi-Fi interface `wlan0` as `up`.
- **E**: Wi-Fi link is down/unavailable, and `eth0` is `up`.
- **-** in the link position: neither tested local interface reports `up`.
- **R** after the link letter: an authenticated ESP32 status request, or an authenticated `source=esp32` reply, arrived at the Pi within 90 seconds.
- **-** in the ESP32 position: no such message arrived within the past 90 seconds.

Example top-right indicators: `WR` means local Wi-Fi link + recent ESP32 bridge traffic, `W-` means Wi-Fi link but no recent messages, `--` means neither local network link nor recent message.

**Important:** W/E mean a local network interface link, not verified Internet access. R means recently received traffic, **not** an active ongoing session or an ESP32 reachability check. In quiet conversation periods, the ESP32 status marker naturally returns to `-`; this does not indicate a malfunction. New valid ESP32 messages restore R.

The menu row now indicates its selection number (e.g. `1/6`) without changing button assignments. The reply/page row and pending-refresh `Q` remain unchanged. Live animated LISTENING, THINKING and SPEAKING symbols remain.

The UI checks the local kernel interface state and the most recent ESP32 request at five-second intervals. It uses no background polling of remote services, no DNS, no IP address display, no credentials, and triggers no e-paper refresh. The ESP32 timestamp is recorded **only after an accepted authenticated status or ESP32-sourced reply**.

The `Pi status` e-paper page additionally describes the local interface link and recency of the ESP32's last signal. This status page refresh still obeys the existing 180-second e-paper cooldown.

## A. Software-only checks while the known-good application keeps running

SSH into the Pi:

```bash
cd ~/hey-muse-github-backup
git fetch origin
git switch --track origin/feature/phase6b-network-menu-2026-11
cd raspberry-pi
python3 -m py_compile muse_pi.py
python3 -m unittest discover -s tests -p 'test_network_menu.py'
python3 -m unittest discover -s tests -p 'test_oled_status.py'
python3 -m unittest discover -s tests -p 'test_single_instance.py'
python3 -m unittest discover -s tests -p 'test_pagination.py'
```

If the new branch was already checked out, use `git switch feature/phase6b-network-menu-2026-11` and `git pull --ff-only`. The tests require no hardware access and do not interfere with the running service. Stop on any failure; do not deploy until corrected.

## B. Back up the working application and install this update

Only after A passes. Wait for any e-paper refresh to finish.

```bash
cd ~/hey-muse-display
cp -p muse_pi.py "muse_pi.before_phase6b_$(date +%Y%m%d_%H%M%S).py"
ls -lt muse_pi.before_phase6b_*.py | head -3
sudo systemctl stop hey-muse-pi.service
cp ~/hey-muse-github-backup/raspberry-pi/muse_pi.py ~/hey-muse-display/muse_pi.py
python3 -m py_compile ~/hey-muse-display/muse_pi.py
sudo systemctl start hey-muse-pi.service
```

Existing conversation history, e-paper refresh state, local token, ESP32 firmware, and systemd unit are unchanged.

## C. Physical acceptance

```bash
systemctl status hey-muse-pi.service --no-pager
curl -fsS http://127.0.0.1:8765/health
```

If the health check runs before the HTTP listener is ready, retry after a few seconds.

1. OLED normally shows W or E when the corresponding Pi link is up.
2. Ask Hey Muse a short question; while messages arrive, R appears at the top right and the existing waveform/dots animations continue.
3. During 90 seconds of quiet, R reverts to - (this is normal). New requests show R again.
4. UP/DOWN changes menu selection count (e.g. 1/6 → 2/6); SELECT and KEY1/KEY2/KEY3 still work.
5. Pending e-paper page navigation and the 180-second cooldown still work.
6. Reply storage, Fish Audio speech and multi-page e-paper output remain unaffected.
7. Optional: use Pi status menu to display the network summary on the e-paper when the cooldown permits.

The Raspberry Pi local link indication may briefly show '-' during Wi-Fi reconnection even while systemd is running. Do not deliberately interrupt Wi-Fi during the first hardware test.

## Rollback

```bash
sudo systemctl stop hey-muse-pi.service
cd ~/hey-muse-display
ls -lt muse_pi.before_phase6b_*.py | head
# Replace the placeholder with the real saved filename
cp -p muse_pi.before_phase6b_YYYYMMDD_HHMMSS.py muse_pi.py
python3 -m py_compile muse_pi.py
sudo systemctl start hey-muse-pi.service
```

Never delete `conversation_history.jsonl`, `refresh_state.json`, or the bearer token while rolling back.

## Acceptance checklist

- [ ] Four software test suites pass on Raspberry Pi
- [ ] Network link indicator and recent-ESP32 marker correct
- [ ] Existing live OLED animations intact
- [ ] Menu position and button operation correct
- [ ] E-paper pagination, 180-second cooldown and Fish Audio intact
- [ ] systemd service continues running normally

## Pi pre-deployment test results — 2026-11-15

The user fetched and switched to the Phase 6b branch on the Raspberry Pi and reported:

- `python3 -m py_compile muse_pi.py`: **PASS**
- `test_network_menu.py`: **4 tests PASS**
- `test_oled_status.py`: **5 tests PASS**
- `test_single_instance.py`: **2 tests PASS**
- `test_pagination.py`: **3 tests PASS**

Total: **14 software tests PASS**. Physical deployment and regression checks remain pending; preserve a dated copy of the running Phase 6a script before stopping the systemd unit to update the working program.

## Startup regression found during first physical deployment — 2026-11-15

The user reported the OLED showing the menu for about 1 second, going blank for several seconds, and repeating. This is consistent with the systemd restart loop. Source inspection located the issue: the UI loop compared `now >= next_link_check` **before** executing `now = time.monotonic()` on its first iteration. This raises `UnboundLocalError`, and the service then restarts. This root cause is derived from source inspection; the user has not yet supplied `journalctl` confirming the exact exception.

**Immediate recovery:** Stop `hey-muse-pi.service`, restore the latest local `muse_pi.before_phase6b_*.py` backup, recompile, and restart systemd. Do not change history files, credentials, or the ESP32.

**Development fix:** commit `dbc5ae2` moves monotonic clock assignment above the network check. Follow-on commit `f979f15` adds a focused AST regression test ensuring the main UI loop initialises `now` before evaluating network timers.

**Status: deployment FAILED on initial Phase 6b version. Code fix prepared in branch; NOT YET VERIFIED on Raspberry Pi.** After recovery, obtain the last 40 journal entries if the service still restarts. Do not replace the running, recovered Phase 6a code until the updated tests pass and the user is ready to retry a controlled deployment.

## Recovery confirmation — 2026-11-15

The user restored the live application from the pre-Phase-6b Phase 6a backup and confirmed: **"After restored to Phase 6a, it works again."**

- [x] Phase 6a recovery after Phase 6b startup failure: **PASS (user-observed)**
- [ ] Corrected Phase 6b code and new regression test run on Raspberry Pi
- [ ] Controlled Phase 6b redeployment and physical acceptance

**Live system is back on the user-tested Phase 6a version. Do not overwrite it until the corrected development branch passes Pi tests.**

## Corrected-source software retest — 2026-11-15

After recovering the working Phase 6a system, the user updated the Phase 6b source checkout and tested the corrected implementation on their Raspberry Pi:

- `python3 -m py_compile muse_pi.py`: **PASS**
- `test_network_menu.py`: **5 tests PASS**
- `test_oled_status.py`: **5 tests PASS**
- `test_single_instance.py`: **2 tests PASS**
- `test_pagination.py`: **3 tests PASS**
- `grep` confirmed `now = time.monotonic()` on line 850 before `if now >= next_link_check:` on line 853.

**15 tests PASS plus startup fix verified in checked-out source.** This is software validation only; corrected Phase 6b has not yet been redeployed or validated against hardware. Retain Phase 6a backup and inspect systemd restart count / application logs after the next controlled deployment.

## Physical test follow-up — 2026-11-15: e-paper cooldown and long TTS

The user reported that the OLED menu works following the corrected Phase 6b deployment. Two remaining issues were observed: e-paper pages did not refresh after an expected 30-second wait, and spoken output stopped partway through a long multi-page reply.

Code inspection found **two independent known limits**:

1. `raspberry-pi/systemd/hey-muse-pi.service` sets `MUSE_EPAPER_REFRESH_SECONDS=180` and the Pi program defaults to 180, with a minimum of 30. The 30-second mode is intended only for short supervised tests. E-paper updates also take hardware time after cooldown expires. The delayed pages are consistent with the current configured 180-second cooldown and not yet proven a new software regression.
2. `esp32/components/muse/muse_chat_session.cpp` uses `TEXT_MAX=1024` for spoken caption/Fish Audio input, while `PI_REPLY_MAX_BYTES=8192` independently sends longer replies to the Pi. The `start_tts()` path still passes the 1 KB caption text to `muse_fish_tts_generate()`. This is a plausible deterministic cause of long e-paper answers exceeding spoken text. It is not caused by the Pi OLED network indicators. Longer TTS remains a separate ESP32 firmware enhancement; no untested changes have been deployed.

**Phase 6b acceptance:** OLED menu reported working, but end-to-end long-reply speech and requested 30-second test mode remain to be addressed / confirmed. Keep the previous Phase 6a backup available. Before any TTS firmware changes, design bounded UTF-8-safe chunking, account for Fish Audio request costs, and verify end-of-audio handling on hardware.

## Corrected Phase 6b live runtime and refresh override logs — 2026-11-15

User shared journal/systemd output from corrected Phase 6b deployment:

- Service `active`; `MainPID=10220`, `NRestarts=0` after 15 seconds.
- Local `/health` returned `{"status":"ok","service":"hey-muse-pi-bridge"}`.
- Pi logs show authenticated ESP32 status and reply HTTP requests returning `202`, a received reply, and completed e-paper refreshes.
- Under 180-second configuration: e-paper job started 17:26:31 and finished 17:27:18 (~47s); page request at 17:27:45 reported 106s remaining; queued refresh started 17:29:33 and finished 17:30:20. This is consistent with cooldown measured from refresh **start**, not completion.
- A temporary systemd drop-in `MUSE_EPAPER_REFRESH_SECONDS=30` was created. `systemctl show ... -p Environment` confirmed `MUSE_EPAPER_REFRESH_SECONDS=30` after daemon reload and restart, but the included journal output did **not** show the new application's startup cooldown line or a new 30-second physical navigation test.
- User removed `/etc/systemd/system/hey-muse-pi.service.d/refresh-test.conf`, reloaded systemd and restarted the service. Expected fallback: 180 seconds; final post-removal environment still unverified by logs.
- User previously reported long Fish Audio speech ending before the longer e-paper answer finishes. Code inspection identified independent 1,024-byte TTS input vs 8,192-byte Pi forwarding; this remains a separate ESP32 firmware limitation and is **not resolved** by the Pi service override.

**Status:** corrected Phase 6b startup stability verified; long-voice and 30-second physical e-paper behaviour not marked accepted. Avoid changing e-paper settings permanently for rapid refresh testing.

## Refresh override restoration verified — 2026-11-15

User supplied post-rollback output:

- `systemctl show hey-muse-pi.service -p Environment` → `PYTHONUNBUFFERED=1 MUSE_EPAPER_REFRESH_SECONDS=180`.
- Previous process PID 10840 logged `Refresh cooldown: 30s.` on startup at 18:50:19, then stopped cleanly at 18:52:45–18:52:46.
- Replacement process PID 11038 started at 18:52:46 and logged `Refresh cooldown: 180s.` at 18:52:48.

**PASS: 30-second temporary override removed and 180-second service/application cooldown restored.** This is independent of the ESP32 Fish Audio long-reply cutoff, which remains to be addressed.
