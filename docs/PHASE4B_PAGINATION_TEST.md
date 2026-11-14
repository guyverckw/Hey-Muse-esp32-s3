# Phase 4b — Queued multi-page navigation

This is a **development branch**, not a tested live-device release. The working backup remains on `backup/full-working-2026-11`.

## Changes

- LEFT / RIGHT and KEY3 page changes are retained when a physical e-paper job is running or the refresh cooldown is active.
- The latest manual button selection takes precedence when the panel becomes available.
- Page count for OLED and Pi status now uses the correct content profile.
- The OLED subtitle adds `Q` when a manual page change is queued.
- Automatic replies and live LISTENING / THINKING / SPEAKING / READY handling retain their existing paths.
- Normal cooldown stays **180 seconds**. An explicit `MUSE_EPAPER_REFRESH_SECONDS=30` environment setting enables a short supervised 30-second test. Waveshare recommends at least 180 seconds on three-colour panels; **30 seconds is outside that recommendation and might accelerate wear or ghosting**. No overlapping e-paper refreshes are allowed.
- The ESP32 firmware's 1,023-byte forwarding limit is **not fixed in this change**. Long reply pagination can be tested by sending a longer sample directly to the Pi's authenticated HTTP inbox, without flashing an ESP32.

## No-GPIO checks (staging checkout)

In the Pi's existing backup checkout, **do not overwrite** the running `~/hey-muse-display` until tests succeed:

```bash
cd ~/hey-muse-github-backup
git fetch origin
git switch --track origin/feature/epaper-queued-pagination-2026-11
cd raspberry-pi
python3 -m py_compile muse_pi.py
python3 -m unittest discover -s tests -p 'test_pagination.py'
python3 muse_pi.py --preview
```

If the feature branch already exists locally, use `git switch feature/epaper-queued-pagination-2026-11 && git pull --ff-only` instead.

Test-only validation renders images to PNG without GPIO. This does **not** prove that physical button handling or automatic refresh have passed a real-device test.

## Safe physical test plan

After you back up the live `muse_pi.py`, shut down its single running process and deliberately copy the tested candidate into `~/hey-muse-display/muse_pi.py`. Then restart **one** instance:

```bash
cd ~/hey-muse-display
MUSE_EPAPER_REFRESH_SECONDS=30 python3 muse_pi.py --listen 0.0.0.0
```

Prefer the 180-second default for normal operation. Test a deliberately long reply (e.g. Pi-local authenticated `POST /api/v1/reply` with 2,000+ characters); the e-paper should display `1/N`, with `N > 1`. Press RIGHT twice during an active refresh/cooldown: the newest requested page should remain queued rather than vanish. The OLED page subtitle should show `Q` until a refresh is scheduled. Confirm normal OLED status transitions and new auto-replies. Record any errors.

The queued-page implementation intentionally does not flash firmware, change hardware drivers or modify persisted refresh history.

## Known limitations

- The OLED shows the **requested** page while queued; the physical e-paper continues to show the previous page until refresh completes.
- Multiple presses during the cooldown coalesce to the most recent selected page.
- Pending automatic newest-reply updates may display after manual page browsing once the next cooldown expires.
- No software change removes the panel's physical refresh time.
