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

**Hardware baseline PASSED on the user's physical board:** the Waveshare ESP-IDF v5.3.2 example compiled, was flashed, displayed its UI, and responded to touchscreen input. The board pin mappings below match the vendor example that was flashed successfully. Audio has not yet been tested. Avoid changing these mappings without a new hardware test.

| Function | Working Waveshare example source |
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

1. **Done:** Build and flash the Waveshare peripheral test using ESP-IDF 5.3.2. Confirm the display and touch on real hardware.
2. **Next:** Implement an independently selectable LCD/touch test image for ESP-IDF 6, leaving the 1.75-inch Muse board untouched.
3. Test LCD colours, coordinate orientation, touch mapping and expander reset under ESP-IDF 6.
4. Test mic, speaker and simultaneous recording/playback using the correct I2S wiring.
5. Add an isolated Muse board profile, SDK overlay and build target; later integrate wake word, Fish Audio, Pi bridge and AEC.

Do not erase or flash the **existing 1.75-inch** device by accident. Identify the USB port with the new board connected before each flash.

## Verified vendor code paths

- `main/LCD_Driver/ST77916.h`, `.c`: QSPI ST77916 init, alternate vendor init table, read-register decision, PWM backlight.
- `main/LCD_Driver/esp_lcd_st77916`: vendor panel driver to adapt to ESP-IDF 6.
- `main/Touch_Driver/CST816.h`, `.c`: touch on separate I2C bus, address 0x15.
- `main/EXIO/TCA9554PWR.c`: GPIO expander output registers (LCD reset EXIO2).
- `main/I2C_Driver/I2C_Driver.c`: sensor/expander I2C bus.
- `main/LVGL_Driver`: LVGL v8 glue, **not directly compatible with Muse's LVGL v9**.

The Waveshare display init contains a register `0x04` read and a case-specific alternate initialization command table; preserve this behaviour. The original test firmware uses `esp_lcd_new_panel_st77916` with quad-SPI and an 80 MHz clock; validate timings on IDF 6 instead of assuming the vendor library ports unchanged.
