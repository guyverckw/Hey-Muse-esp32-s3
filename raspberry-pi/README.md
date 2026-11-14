# Hey Muse — Raspberry Pi display companion

This directory contains the Raspberry Pi 3B companion code backed up from the working Hey Muse setup in November 2026.

**Full recovery instructions:** [Hey Muse Recovery Guide](../docs/HEY_MUSE_RECOVERY.md).

## Source files

- `muse_pi.py`: live HTTP bridge, OLED status display, e-paper rendering and button navigation.
- `waveshare_epd/`: Waveshare 5.83-inch three-colour e-paper drivers used on the Pi.
- `tests/`: hardware verification scripts (run only after stopping any other GPIO-controlling process).
- `installers/`: historical patch/install scripts retained as development reference; do **not** rerun against the already-patched live program.
- `legacy/`: historical Phase 1 version.

## Known-good snapshot vs running installation

The source was copied from `/home/musepi/hey-muse-display/` into the GitHub branch `backup/full-working-2026-11`. It is a **source backup**, not a verified clean-machine restore. Preserve the working Pi directory.

The committed `muse_pi.py` uses `MIN_REFRESH_SECONDS = 180`, with compact AI reply formatting at 600×448 pixels. Later changes made directly on the Pi should be deliberately reviewed and committed before considering this an up-to-date backup.

## Safe checks

```bash
cd raspberry-pi
python3 -m py_compile muse_pi.py
python3 muse_pi.py --preview
```

Preview mode does not initialise the displays. To run live hardware, see the recovery guide; don't run multiple GPIO-controlling processes simultaneously.

## Security

The GitHub repository is public. Keep the Pi bearer token (`~/.config/hey-muse-pi/bridge_token`), live conversation history, refresh state, SDK credentials, Wi-Fi information, API keys, and the ESP32 private bridge configuration outside Git. Before committing new or changed files, check staged diffs for accidentally embedded secrets.

The ignore rules reduce accidental uploads but **do not** protect files already tracked or files stored in other directories.
