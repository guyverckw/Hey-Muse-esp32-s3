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

## Mac build verification — 2026-11-21

User ran both firmware builds on Intel macOS with ESP-IDF 6.0 and reported successful script completion. The provided command outputs ended in ESP-IDF/esptool flash instructions, not build errors:

- **Standalone:** `tools/muse/board.sh build s3n` — **PASS**, produced `build-muse-waveshare-s3-175/muse-gadget.bin`.
- **Pi companion:** `MUSE_PI_BRIDGE=1 tools/muse/board.sh build s3n` — **PASS**, produced `build-muse-waveshare-s3-175-pi/muse-gadget.bin`.

These were build-only commands. **No flash or on-device test was reported.** The user did not yet provide Python regression-test output, explicit build-time Kconfig settings, linker maps or firmware sizes, so those are **pending verification**.

For the next check, run from `esp32/`:

```bash
printf 'Standalone config: '; grep -E '^CONFIG_MUSE_PI_BRIDGE=|^# CONFIG_MUSE_PI_BRIDGE is not set' build-muse-waveshare-s3-175/sdkconfig
printf 'Pi-enabled config: '; grep -E '^CONFIG_MUSE_PI_BRIDGE=|^# CONFIG_MUSE_PI_BRIDGE is not set' build-muse-waveshare-s3-175-pi/sdkconfig
ls -lh build-muse-waveshare-s3-175/muse-gadget.bin build-muse-waveshare-s3-175-pi/muse-gadget.bin
find build-muse-waveshare-s3-175 build-muse-waveshare-s3-175-pi -maxdepth 1 -name '*.map' -print
```

Inspect the linker map or `compile_commands.json` for `muse_pi_bridge.cpp` to establish actual omission in standalone output. Do not treat two successful builds alone as measured proof of binary omission. Keep the user-tested stable baseline and current live ESP32 firmware unchanged.

## Build profile and compilation verification — 2026-11-21 (user-reported)

On the Mac, after both S3N ESP-IDF builds succeeded, the user inspected the generated `sdkconfig`, `compile_commands.json`, and `muse-gadget.bin`:

| Test | Standalone | Raspberry Pi companion |
| --- | --- | --- |
| Kconfig value | `# CONFIG_MUSE_PI_BRIDGE is not set` | `CONFIG_MUSE_PI_BRIDGE=y` |
| `muse_pi_bridge.cpp` in compilation database | **NO** | **YES** |
| `muse-gadget.bin` size | **3,674,112 bytes** | **3,674,112 bytes** |

**Result: PASS for profile selection and compilation isolation.** Both images exist and both ESP-IDF builds previously completed successfully. An identical image length does **not** prove equal contents, equal linked code size, or absence of savings. ESP-IDF image alignment or other differences may explain it. Binary/ELF hashes, linker-map comparison, and physical hardware testing are still pending; **no devices have been flashed with these modular images**.

For optional additional comparison from `esp32/`:

```bash
shasum -a 256 build-muse-waveshare-s3-175/muse-gadget.bin build-muse-waveshare-s3-175-pi/muse-gadget.bin
python3 - <<'PY'
from pathlib import Path
for d in ('build-muse-waveshare-s3-175', 'build-muse-waveshare-s3-175-pi'):
    p = Path(d)
    elf = p / 'muse-gadget.elf'
    print(d, 'ELF bytes:', elf.stat().st_size, 'map:', (p / 'muse-gadget.map').exists())
PY
```

Future hardware verification should run both builds on appropriate test devices and preserve the existing accepted production baseline.

## Artifact hash comparison — 2026-11-21 (user-reported)

The user compared the two Mac-generated firmware image hashes and the ELF file sizes:

| Output | Standalone ESP32 | Raspberry Pi companion |
| --- | --- | --- |
| `muse-gadget.bin` SHA-256 | `b1802c7f5c4b91cc9bf605f99f306519c4a9c19a1e82358b62b4438f04ad517a` | `84be38cf1a080c6a591ac2e69ec59e6ab322edc5b34a012e30d0c52002909f4e` |
| `muse-gadget.bin` length | 3,674,112 bytes | 3,674,112 bytes |
| `muse-gadget.elf` size (rounded by `ls -lh`) | 29 MB | 29 MB |

**Verification:** SHA-256 hashes differ, so the two generated binary files have different contents. The compilation database previously showed that `muse_pi_bridge.cpp` is not compiled in standalone and is compiled in companion mode. Identical image lengths and rounded ELF sizes do not establish equal linked section sizes or prove any specific flash/RAM savings. Both modes still require physical acceptance testing.

Next optional comparison on the Mac with ESP-IDF toolchain exported:

```bash
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3/esp32
idf.py -B build-muse-waveshare-s3-175 size
idf.py -B build-muse-waveshare-s3-175-pi size
```

This compares linked section usage without flashing hardware. Keep this PR in draft until hardware tests pass.

## Actual linked memory comparison — 2026-11-21 (user-provided `idf.py size` logs)

User executed `idf.py -B build-muse-waveshare-s3-175 size` and `idf.py -B build-muse-waveshare-s3-175-pi size` on macOS. Both completed with memory summaries:

| Reported category | Standalone (bytes) | Pi companion (bytes) | Pi minus standalone |
| --- | ---: | ---: | ---: |
| Flash Data | 1,803,672 | 1,804,264 | +592 |
| Flash Code | 1,693,612 | 1,694,924 | +1,312 |
| DIRAM total used | 170,421 | 170,421 | 0 |
| External RAM static used | 33,008 | 33,008 | 0 |
| RTC SLOW used | 2,096 | 2,096 | 0 |
| RTC FAST used | 72 | 72 | 0 |
| **Reported total image size** | **3,629,525** | **3,631,429** | **+1,904** |

Conclusion: standalone mode excludes the Pi bridge source from compilation and reduces the **linked image** by **1,904 bytes** (roughly 1.9 KB). Earlier reported padded `.bin` files remain equal at 3,674,112 bytes, and both ELF files round to 29 MB on `ls -lh`. The equal static RAM figures do **not** imply equal runtime heap usage: the Pi HTTP worker, queue and allocations are created when used.

The standalone `size` action re-ran CMake and dependency processing, producing multiple version/compatibility, unknown Kconfig-symbol and deprecated-CMake warnings, and printed a `Missing kconfig option. Re-run the build process...` warning. Despite that, the provided log reached a successful memory-size summary for both configurations; no fatal compilation error was visible in the provided excerpt. Warnings should be tracked separately if they recur in clean builds; do not conflate them with a modularization failure.

**Verification status:** profile flags, separate source compilation, differing firmware hashes, and linked memory comparison all passed. **Physical flashing and standalone/companion device acceptance are still pending.** Leave existing user-tested hardware and `stable/hey-muse-2026-11-21-wake-tested` unchanged until the user chooses hardware tests.

## Hardware testing decision — 2026-11-21

The user does **not** have a spare ESP32 identical to the working Hey Muse board and explicitly elected to **skip flashing and hardware testing** of the modular profiles, to avoid risking the current stable device.

**Final scope/status for this change: desktop build-verified, not hardware-validated.**

- Both standalone and Pi companion configurations compiled successfully on macOS with ESP-IDF 6.
- Generated Kconfig and compilation database confirm the intended module exclusion/inclusion.
- Linked memory summaries and hashes were compared; standalone linked image is 1,904 bytes smaller.
- Neither modular image was flashed or functionally tested on a physical device.
- No claim of hardware acceptance or compatibility with other boards is made.
- Do not require an extra identical ESP32 from this user or propose flashing their stable setup for this feature.

Preserve `stable/hey-muse-2026-11-21-wake-tested` as the **last user-confirmed hardware-tested baseline**. Keep the modular changes available on `feature/modular-esp32-pi-bridge-2026-11` / draft PR #8, labelled compile-verified until future hardware evidence is supplied. Future users can test on compatible hardware at their own discretion.
