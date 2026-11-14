# Phase 5 — Raspberry Pi automatic startup and recovery

**Status: implementation staged on GitHub; not yet tested or deployed on the physical Pi.**

- Stable source snapshot: `backup/phase4c-tested-2026-11`
- Development branch: `feature/phase5-autostart-recovery-2026-11`
- Service: `raspberry-pi/systemd/hey-muse-pi.service`
- Current live Pi directory: `/home/musepi/hey-muse-display`

The deployment retains the same HTTP bridge on port 8765, token path, reply-history path, GPIO pinout, language handling and 4b queued-page functionality. No ESP32 firmware changes are needed.

## Behaviour

- systemd starts the Pi program after the network-online target and restarts it after errors (`Restart=on-failure`, 10-second delay).
- Clean exit via the OLED `Exit` menu stays stopped until manually started or the next reboot. This is deliberate.
- A private OS file lock at `~/.config/hey-muse-pi/muse_pi.lock` prevents simultaneous *Phase 5* processes. The lock is released by the kernel on exit or crash. **Existing pre-Phase-5 programs do not use this lock**: stop the old app before first deployment.
- Stopping the service sends SIGINT so the Python program has a chance to finish a current e-paper operation and close GPIO. Stop may take time if the physical display is busy.
- The service defaults to `MUSE_EPAPER_REFRESH_SECONDS=180` (manufacturer-advised normal use), not the optional 30-second Phase 4b stress-test setting.
- Existing stored replies and refresh cooldown state stay under `~/hey-muse-display`. The Bearer token stays at `~/.config/hey-muse-pi/bridge_token`. **Never copy tokens into Git**.
- No remote messages are replayed automatically if the ESP32 sent them while the Pi bridge was offline. Future ESP32 messages should work again after the listener returns.

## Stage A — Safe checks without changing the live application

On the Pi (leave the existing working program running):

```bash
cd ~/hey-muse-github-backup
git fetch origin
git switch --track origin/feature/phase5-autostart-recovery-2026-11
cd raspberry-pi
python3 -m py_compile muse_pi.py
python3 -m unittest discover -s tests -p 'test_single_instance.py'
python3 -m unittest discover -s tests -p 'test_pagination.py'
python3 muse_pi.py --preview
```

If branch already exists, switch to it and pull `--ff-only`. The preview produces PNGs; it does not use hardware. The singleton unit tests use a temporary directory and never touch the live lock or Pi token.

Before installing, check:

```bash
id musepi
command -v python3
python3 -c 'import PIL, gpiozero, spidev, luma.oled; print("Pi dependencies import OK")'
sudo systemd-analyze verify ~/hey-muse-github-backup/raspberry-pi/systemd/hey-muse-pi.service
```

The template expects `/usr/bin/python3`, `musepi`, and `/home/musepi/hey-muse-display`. If your working Python is a virtual environment or different interpreter, **edit the service template before installing**; its interpreter must import all the above modules and your Waveshare driver. A failing `systemd-analyze verify` may be a legitimate installation blocker; inspect its diagnostics.

## Stage B — Preserve the live working installation

Before altering the live app, save its exact source and service state:

```bash
cd ~/hey-muse-display
cp -p muse_pi.py "muse_pi.before_phase5_$(date +%Y%m%d_%H%M%S).py"
sha256sum muse_pi.py ~/hey-muse-github-backup/raspberry-pi/muse_pi.py
systemctl is-enabled hey-muse-pi.service 2>/dev/null || true
systemctl is-active hey-muse-pi.service 2>/dev/null || true
```

Record the backup filename. Keep any prior manual shell session available so you can stop it gracefully with Ctrl+C. Do not publish history, secrets or this backup file.

**Stop the current old-version process** using Ctrl+C in its terminal, then verify:

```bash
ps -eo pid,args | grep '[m]use_pi.py' || true
sudo ss -ltnp '( sport = :8765 )'
```

The first command must show no old application and the second no listener on 8765. If a process remains, determine what launched it and stop it gracefully; do not blindly kill other Python applications.

## Stage C — Install new source and systemd unit (the live change)

Do this only after the non-hardware tests have passed and the old application is stopped.

```bash
cp ~/hey-muse-github-backup/raspberry-pi/muse_pi.py ~/hey-muse-display/muse_pi.py
python3 -m py_compile ~/hey-muse-display/muse_pi.py
sudo install -m 0644 \
  ~/hey-muse-github-backup/raspberry-pi/systemd/hey-muse-pi.service \
  /etc/systemd/system/hey-muse-pi.service
sudo systemctl daemon-reload
sudo systemctl enable --now hey-muse-pi.service
```

If you intend to keep the 30-second experimental interval, it must be a deliberate systemd override rather than editing the tracked service. For normal use, keep 180 seconds.

## Stage D — Validate autostart and failure recovery

```bash
systemctl status hey-muse-pi.service --no-pager
curl -fsS http://127.0.0.1:8765/health
journalctl -u hey-muse-pi.service -n 60 --no-pager
ps -eo pid,args | grep '[m]use_pi.py'
```

Acceptance checks:

1. Only one live `muse_pi.py` process; service shows `active (running)`.
2. Pi `/health` responds with JSON `{"status":"ok"...}`.
3. Verify OLED status, joystick, KEY2, and full e-paper pagination with a regular short Hey Muse question.
4. Test an **orderly restart** with `sudo systemctl restart hey-muse-pi.service`; inspect logs, GPIO behaviour and health. Restart may wait for a running e-paper job.
5. Test the **automatic failure restart** only when not actively refreshing the e-paper: use `sudo systemctl kill -s SIGKILL --kill-who=main hey-muse-pi.service`, then `sleep 15; systemctl is-active hey-muse-pi.service; curl -fsS http://127.0.0.1:8765/health`. An abrupt kill is *not* safe during display refresh; avoid it until no display activity. This is optional but tests `Restart=on-failure`.
6. Once safe and healthy, a reboot test (`sudo reboot`) confirms automatic startup. Reconnect through SSH and inspect `systemctl status` and `curl /health`. Only reboot when you can access the device again.

If `systemctl status` shows restart loops, stop and disable the service, then inspect `journalctl -u hey-muse-pi.service`. Common causes: wrong Python interpreter, unavailable GPIO driver, another process using GPIO or port 8765, insufficient privileges, or a mismatched user/home path.

## Roll back without losing history

```bash
sudo systemctl disable --now hey-muse-pi.service
cd ~/hey-muse-display
# Replace the placeholder with the exact earlier backup filename printed by ls:
ls -lt muse_pi.before_phase5_*.py
cp -p muse_pi.before_phase5_YYYYMMDD_HHMMSS.py muse_pi.py
python3 -m py_compile muse_pi.py
python3 muse_pi.py --listen 0.0.0.0 --port 8765
```

The rollback example does not delete conversation history, bridge token or refresh state. Use your previously working 30-second environment override only if intentionally conducting a short display test; otherwise the app defaults to 180 seconds. Leave the inactive systemd unit installed for future work or remove it separately.

## Definition of done

- [ ] No-GPIO lock/pagination tests pass
- [ ] Service installed with correct working Python and service account
- [ ] Service starts and `/health` succeeds
- [ ] One instance only, including blocked second manual launch
- [ ] Normal Hey Muse reply, speech, OLED and e-paper still work
- [ ] Graceful systemd restart succeeds
- [ ] Automatic failure restart succeeds safely
- [ ] Reboot startup succeeds (tested when convenient)
- [ ] Rollback copy saved and verified

## Hardware deployment progress — 2026-11-14

After staging the Phase 5 source and systemd unit, user supplied the following Raspberry Pi outputs:

- `hey-muse-pi.service`: loaded, **enabled**, **active (running)** (started 2026-11-14 23:19:06 GMT)
- Process: one `/usr/bin/python3 -u /home/musepi/hey-muse-display/muse_pi.py --listen 0.0.0.0 --port 8765` instance (observed PID 58364)
- `curl http://127.0.0.1:8765/health`: `{"status":"ok","service":"hey-muse-pi-bridge"}`
- Service log: displays initialized, bridge listening, refresh cooldown **180s**
- Pre-deployment: Python compilation, two singleton tests, three pagination tests, dependencies and systemd validation all passed

**Status: PASS for initial systemd startup and bridge health; pending controlled restart, live reply/display check, automatic failure recovery and real reboot.** PIDs and timestamps above describe this particular run, not guaranteed future startup values.

## Restart and failure-recovery tests — user report

The user ran a controlled `sudo systemctl restart hey-muse-pi.service`: the unit returned `active` and showed new MainPID **58527**, but an immediately issued `curl /health` failed with connection refused. This is consistent with `Type=simple` reporting active before Python has bound port 8765; **HTTP readiness after that controlled restart was not confirmed in that same test**.

The user then executed `sudo systemctl kill -s SIGKILL --kill-who=main hey-muse-pi.service`, waited 15 seconds, and observed `active`, MainPID **58587**, and `NRestarts=1`. The pasted `curl` output was partially garbled but appears to show the bridge's JSON health response. **Unexpected-failure restart: PASS; bridge readiness: very likely PASS, independently recheck with an explicit retry loop.** Do not infer clean boot recovery until an actual reboot test.

Recommended readiness probe (no hardware side effects):

```bash
for i in $(seq 1 20); do
  if curl -fsS --max-time 2 http://127.0.0.1:8765/health; then
    echo "HTTP bridge ready (attempt $i)"
    break
  fi
  sleep 1
done
```

Note that `Type=simple` is not a readiness protocol; avoid interpreting an immediate port refusal as failure while the program is starting. Do not change to `Type=notify` without implementing `sd_notify` in the application.

## Reboot acceptance result — 2026-11-14 (user-observed)

After an actual Raspberry Pi reboot, the user reconnected via SSH and reported:

- `systemctl is-enabled hey-muse-pi.service` → **enabled**
- `systemctl is-active hey-muse-pi.service` → **active**
- `curl -fsS http://127.0.0.1:8765/health` → bridge JSON health response, `status: ok` (pasted output interleaved with other lines)
- `systemctl show ... -p MainPID -p NRestarts` → **MainPID=1345**, **NRestarts=0**

**Boot persistence and HTTP startup: PASS.** Prior simulated crash recovery: **PASS**. Prior single-instance/pagination unit tests: **PASS**. Live hardware interaction after reboot (OLED/e-paper buttons, new ESP32 reply) has not yet been separately reported and remains a final functional regression check.
