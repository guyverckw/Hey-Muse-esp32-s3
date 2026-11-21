# Modular ESP32 firmware: standalone or Raspberry Pi companion

**Development status:** source changes committed on `feature/modular-esp32-pi-bridge-2026-11`. Builds and hardware testing of both modes are **pending**. The accepted firmware/Pi baseline remains unchanged at `stable/hey-muse-2026-11-21-wake-tested`.

## What is configurable

| Mode | Default | Pi bridge code | Connection |
| --- | --- | --- | --- |
| Standalone | Yes | Excluded from compilation/link | Muse app + Muse agent; Fish Audio voice and supported wake/animations as before |
| Pi companion | Opt in | Included with HTTP status/reply worker | Same ESP32 functionality plus authenticated Pi OLED/e-paper forwarding |

Enable the Raspberry Pi companion with the Kconfig option `CONFIG_MUSE_PI_BRIDGE=y`. The default is **disabled**. The bridge is available when `CONFIG_MUSE_HATCH=y`; it is not a requirement for a standalone ESP32.

Only `muse_pi_bridge.cpp` is excluded from the binary in standalone mode. The existing full-reply buffer in `muse_chat_session.cpp` must remain because **full-length Fish Audio depends on it even without a Pi**. The bridge API's disabled implementation is a small inline no-op in `muse_pi_bridge.h`.

## Select modes on a Waveshare 1.75-B board

From `esp32/` on a Mac/Linux development machine with ESP-IDF v6.0.1 configured:

### Standalone (default)

```bash
. ~/esp/esp-idf-v6/export.sh
tools/muse/board.sh build s3n
# If selecting the standalone image for flashing:
tools/muse/board.sh flash s3n
```

Build directory: `build-muse-waveshare-s3-175/`. Does **not** require a Pi IP, token, or bridge configuration header.

### ESP32 + Pi companion (opt in)

Create the secret-bearing local config file without tracking it:

```bash
cd esp32/components/muse
cp muse_pi_bridge_config.h.example muse_pi_bridge_config.h
# Edit URL to your Pi's /api/v1/reply endpoint and token locally.
# NEVER commit actual tokens, Wi-Fi credentials, or flash backups.
cd ../../
```

The `cd ../../` above returns to `esp32/` from `esp32/components/muse/`. The example uses placeholders only; real config values must be installed on the local development host.

```bash
. ~/esp/esp-idf-v6/export.sh
MUSE_PI_BRIDGE=1 tools/muse/board.sh build s3n
# After a successful build, if you intend to flash Pi companion mode:
MUSE_PI_BRIDGE=1 tools/muse/board.sh flash s3n
```

Build directory: `build-muse-waveshare-s3-175-pi/`. The source includes `muse_pi_bridge.cpp`, and the bridge requires the local `muse_pi_bridge_config.h`. An absent config header gives a clear configuration error. Use the existing Pi service's bearer token; don't paste it into a GitHub issue or PR.

**Warning:** The Pi companion's existing private header on the user's Mac is not checked in. The Pi-enabled build therefore cannot be rebuilt from GitHub alone without the user's own local bridge settings (by design).

**Important:** `build` and `flash` must both use the *same* `MUSE_PI_BRIDGE` environment setting. The two modes have different directories so switching modes won't accidentally flash the wrong build.

## Other supported boards

Use the existing board targets, e.g. `s3`, `box3`, `watcher`, etc.; see `tools/muse/board.sh` for valid targets. Their hardware support and wake model differ, so don't assume that features tested on `s3n` work on every board. The optional bridge requires Hatch to be enabled and a working Pi service.

## Safety and verification

1. Preserve your already working hardware — **do not flash the stable devices to verify build-time modularity**.
2. Run the source-level test:

   ```bash
   python3 -m unittest esp32/tests/test_modular_pi_build.py
   ```

3. Configure local Pi header as needed and compile **both** profiles, one at a time (the helper cleans managed components between builds):

   ```bash
   cd esp32
   tools/muse/board.sh build s3n
   MUSE_PI_BRIDGE=1 tools/muse/board.sh build s3n
   ```

4. Verify generated settings:

   ```bash
   grep '^CONFIG_MUSE_PI_BRIDGE=' build-muse-waveshare-s3-175-pi/sdkconfig
   grep -E '^(# CONFIG_MUSE_PI_BRIDGE is not set|CONFIG_MUSE_PI_BRIDGE=)' build-muse-waveshare-s3-175/sdkconfig
   ```

5. Check actual linker output / map file to confirm `muse_pi_bridge.cpp` is excluded from the standalone binary. Compare compiled flash sizes if desired; don't invent size savings before measuring.
6. **Later**, hardware acceptance of standalone and Pi companion images should confirm Muse pairing, wake, Fish TTS, and for companion mode, OLED transitions and full e-paper replies.
7. Existing Pi systemd override `MUSE_EPAPER_REFRESH_SECONDS=30` is independent of this ESP32 setting and untouched.

## Notes for developers

- The default standalone build leaves `CONFIG_MUSE_PI_BRIDGE` disabled and compiles Pi API calls into no-ops, without requiring a bridge token.
- The optional Pi bridge currently uses a manually supplied local header and fixed endpoint; future work could move that into secure on-device settings, but **not required** for this modular build.
- Separate build folders prevent Pi-enabled/standalone SDKCONFIG and flash arguments from overwriting each other.
- The original stable source and both user-created backup copies remain intact.
