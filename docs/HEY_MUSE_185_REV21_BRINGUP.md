# Hey Muse Device #2 — Waveshare ESP32-S3-Touch-LCD-1.85

**Status (2026-11-22):** Board serial communication and memory detected; display/touch/audio firmware not yet built or flashed.

## Confirmed from the connected board (read-only esptool)

- ESP32-S3, revision v0.2
- 8 MB embedded PSRAM
- 16 MB quad-SPI flash at 3.3 V
- USB-Serial/JTAG at `/dev/cu.usbmodem14201` (port can change on reconnect)
- User waived backing up previous, nonworking firmware

## Sources and safety note

- [Waveshare hardware documentation and general pin table](https://docs.waveshare.com/ESP32-S3-Touch-LCD-1.85)
- [Waveshare ESP-IDF peripheral-test example](https://github.com/waveshareteam/ESP32-S3-Touch-LCD-1.85/tree/main/examples/esp-idf/ESP32-S3-Touch-LCD-1.85-Test)
- [Rev 2.1 schematic](https://files.waveshare.com/wiki/ESP32-S3-Touch-LCD-1.85/ESP32-S3-Touch-LCD-1.85_V2.1.pdf)

**Important:** An earlier draft of this document contained an **unverified, conflicting pin table**. It has been removed. The table below is from the official *generic product documentation* and is **not yet verified against Rev 2.1 vendor firmware/schematic**. Avoid driving LCD GPIOs until the exact PCB revision's vendor test source has been checked.

| Function | Official product documentation |
| --- | --- |
| QSPI LCD D0/D1/D2/D3 | GPIO46/45/42/41 |
| QSPI LCD CLK/CS/TE | GPIO40/21/18 |
| LCD RESET / backlight | Expander EXIO2 / GPIO5 |
| Touch SDA/SCL/INT / RESET | GPIO1/3/4 / expander EXIO1 |
| Shared peripheral I2C SDA/SCL | GPIO11/10 |
| Microphone WS/SCK/SD | GPIO2/15/39 |
| PCM5101 DIN/LRCK/BCK | GPIO47/38/48 |
| microSD MISO/MOSI/CLK/CS | GPIO16/17/14 / expander EXIO3 |

## Implementation sequence

1. Obtain and inspect the appropriate Waveshare **Rev 2.1** peripheral test example; verify its LCD SPI, touch and GPIO expander mapping.
2. Build a small, independently selectable LCD/touch test image for ESP-IDF, leaving the 1.75-inch Muse board code untouched.
3. Test LCD colours and coordinate orientation, then touch positions and expander reset on hardware.
4. Test mic, speaker and simultaneous recording/playback using the correct I2S wiring.
5. Add an isolated Muse board profile, SDK overlay and build target; later integrate wake word, Fish Audio, Pi bridge and AEC.

Do not erase or flash the **existing 1.75-inch** device by accident. Identify the USB port with the new board connected before each flash.
