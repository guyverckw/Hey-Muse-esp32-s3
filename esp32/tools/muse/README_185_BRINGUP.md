# Waveshare ESP32-S3-Touch-LCD-1.85 — first Hey Muse build

Hardware-tested reference: PCB Rev 2.1, 16MB flash, 8MB octal PSRAM.
Vendor ESP-IDF 5.3.2 test flashed and passed LCD, CST816 touch and "Hi ESP" recognition.
Physical ST77916 register 0x04: `00 02 7f 7f` (case 2).

This branch includes the **first uncompiled/unflashed port** of LCD/touch on ESP-IDF 6.
The original 1.75-inch firmware branches are untouched.
The new target is `s3-185`, with its own sdkconfig and build directory.

## Compile only (do not flash yet)

From a **new Terminal** on the Mac, activate the existing IDF 6 environment:

```sh
. ~/esp/esp-idf-v6/export.sh
idf.py --version
cd ~/Documents/ESP32/MUSE/Hey-Muse-esp32-s3
git fetch origin
git switch feature/hey-muse-waveshare-s3-185-port-2026-11
git pull --ff-only
cd esp32
bash tools/muse/board.sh build s3-185
```

The build script puts the full log at `/tmp/muse_build_s3-185_0.log`.
Afterwards run:

```sh
grep -n -E 'error:|FAILED|undefined reference|fatal error|CMake Error|Project build complete' /tmp/muse_build_s3-185_0.log | tail -30
tail -40 /tmp/muse_build_s3-185_0.log
```

**Do not flash until compilation is confirmed and any IDF 6 API errors fixed.**

## Known limitations of this milestone

- Display/touch only; microphone and speaker are excluded from Muse's audio API.
- The case-2 vendor initialization sequence and vendor LCD panel driver were
  imported and isolated to this target; they may require ESP-IDF 6 compatibility work.
- Power key and battery management are not yet supported in the Muse port.
- The QSPI LCD transfer and touch coordinate mapping have **not** been tested on this
  newly ported firmware. Passing the vendor demo does not imply the port works.
- The Waveshare vendor LCD panel driver is Apache-2.0 licensed; retain its license header.
