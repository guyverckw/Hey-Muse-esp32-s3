#!/usr/bin/env bash
# Read-only inventory of the Waveshare 1.85-inch vendor peripheral test sources.
# Usage: bash tools/muse/inspect_185_vendor.sh [path-to-vendor-test-project]
# Does not build, erase, write, or flash anything.
set -euo pipefail

vendor="${1:-$HOME/Documents/ESP32/MUSE/waveshare-185-reference/examples/esp-idf/ESP32-S3-Touch-LCD-1.85-Test}"
if [[ ! -d "$vendor/components" ]]; then
    echo "Vendor project not found: $vendor" >&2
    exit 1
fi

echo "==== Waveshare 1.85 driver source inventory ===="
find "$vendor/components" -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.h' \) |
    grep -Ei '/(st77916|cst816|tca9554|lvgl|i2c|pcm5101|mic|lcd|touch|board|esp-bsp|bsp)' |
    sed "s|$vendor/||" |
    head -n 100 || true

echo
echo "==== Hardware GPIO, expander, LCD, touch and audio definitions ===="
grep -RnE --include='*.h' --include='*.c' --include='*.cpp' \
    '(#define[[:space:]]+.*(GPIO|PIN|SDA|SCL|SCLK|MOSI|MISO|CS|CLK|BL|RST|RESET|EXIO|I2S|BCK|WS|DIN|DOUT)|gpio_num_t[[:space:]]+|spi_bus_config_t|esp_lcd_panel_io_spi_config_t|i2s_std_gpio_config_t)' \
    "$vendor/main" "$vendor/components" |
    grep -Ei '(ST77916|CST816|TCA9554|PCM5101|MIC|LCD|I2C|BSP|board|Touch|display|lvgl|audio)' |
    sed "s|$vendor/||" |
    head -n 220 || true

echo
echo "==== Actual driver initialization call sites ===="
grep -RnE --include='*.h' --include='*.c' --include='*.cpp' \
    '(LCD_Init|Touch_Init|EXIO_Init|I2C_Init|Audio_Init|MIC_Speech_init|esp_lcd_new_panel|esp_lcd_new_panel_io|spi_bus_initialize|i2c_new_master_bus)' \
    "$vendor/main" "$vendor/components" |
    sed "s|$vendor/||" |
    head -n 140 || true
