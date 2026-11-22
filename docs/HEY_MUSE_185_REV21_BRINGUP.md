# Hey Muse Device #2: Waveshare ESP32-S3-Touch-LCD-1.85 Rev 2.1

**Status:** USB communication and memory verified on physical hardware (2026-11-22). Display/audio port not yet implemented or flashed.

## Verified on the user's Mac

- Device port: `/dev/cu.usbmodem14201` (may change if reconnected)
- ESP32-S3 QFN56 rev v0.2; 8 MB octal PSRAM reported by esptool
- 16 MB quad-SPI, 3.3V flash reported by `esptool flash-id`
- USB Serial/JTAG transport is working.
- Existing firmware can be overwritten: user explicitly waived backup for this second board.
- **Do not touch** the original 1.75-inch stable branch or firmware.

## Revision-sensitive pinout — use the Rev 2.1 schematic

Official schematic: https://files.waveshare.com/wiki/ESP32-S3-LCD-1.85/ESP32-S3-Touch-LCD-1.85_V2.1.pdf

The generic documentation at https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.85 gives a different pin map (for another PCB revision). Do not blindly copy its pins.

The following pins are transcribed from the Rev 2.1 schematic's hardware table and **must be revalidated against vendor demo code** before flashing a display/audio build:

| Subsystem | Rev 2.1 schematic |
| --- | --- |
| Touch SDA, SCL, INT | GPIO1, GPIO2, GPIO3 |
| LCD backlight PWM | GPIO4 |
| LCD CS, CLK | GPIO19, GPIO41 |
| LCD data QSPI D0, D1, D2, D3 | GPIO46, GPIO45, not confirmed, GPIO42 |
| Touch reset | expander EXIO0 |
| LCD reset | expander EXIO1 |
| I2C sensors/expander | GPIO10 SCL, GPIO11 SDA |
| Speaker I2S LRCK, BCK, DIN | GPIO38, GPIO48, GPIO47 |
| Mic data | GPIO39 (other mic pins require verification) |
| SD SPI SCLK, MISO, MOSI, CS | GPIO14, GPIO15, GPIO16, expander EXIO2 |

**Attention:** The schematic table does not clearly assign every display data bit. The QSPI D2 pin and exact mic clock/input need inspection in the actual vendor sample and schematic before code is authored.

## Port stages

1. Create a standalone, *new-board-only* ESP-IDF bring-up target for GPIO expander, LCD, backlight and touch.
2. Verify display colours, 360×360 clipping, touch coordinate mapping, power/reset, I2C scan and serial logging.
3. Verify mic capture and speaker output, including simultaneous full-duplex I2S where supported.
4. Add a separate Muse board implementation (do not modify existing 1.75-inch board implementation), Kconfig device ID, sdkconfig overlay, managed component rules, and independent build directory.
5. Enable wake-word, Fish Audio, Pi bridge and AEC only after device-specific audio performance is validated.

All flashing must explicitly target the port of the *second* board.
