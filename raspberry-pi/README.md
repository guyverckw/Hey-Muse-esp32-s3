# Hey Muse — Raspberry Pi display companion

This directory is intended for the **Raspberry Pi 3B** runtime source that works with the ESP32 Hey Muse firmware.

## Current sync status
The actual latest Raspberry Pi source has **not yet been uploaded** to this GitHub branch. The running copy currently lives on the Pi at `/home/musepi/hey-muse-display`. Copy and review that code before committing.

Expected code includes `muse_pi.py` (OLED status, HTTP reply inbox, compact 17-line e-paper rendering, Chinese/Japanese text, async refresh and physical-button page navigation), plus any **locally modified** Waveshare driver Python modules and supporting scripts.

## Do not commit
Do not upload `/home/musepi/.config/hey-muse-pi/bridge_token`, environment files, Fish Audio/API credentials, Wi-Fi credentials, stored conversations, runtime state or backups. Scan even non-ignored text files for hardcoded secrets before committing.

## Upload approach
From the Pi, clone the repository to a separate directory, check out the `backup/raspberry-pi-source-2026-11` branch, copy only inspected source files under `raspberry-pi/`, then stage those paths explicitly and push the branch.

Never replace the working `~/hey-muse-display` directory or restart the running application merely to make a backup.

## Verification
Compare SHA-256 hashes of the Pi source and its committed copy. Run `python3 -m py_compile muse_pi.py` before and after copying. For a reproducible deployment, document apt/pip requirements and display wiring without uploading machine-specific secrets.
