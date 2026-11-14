
from luma.core.interface.serial import spi
from luma.oled.device import sh1106
from luma.core.render import canvas
import time

print("Initialising Waveshare 1.3-inch OLED...")

# Waveshare OLED HAT default 4-wire SPI configuration
serial = spi(
    port=0,
    device=0,
    gpio_DC=24,
    gpio_RST=25,
    bus_speed_hz=8000000
)

display = sh1106(serial, width=128, height=64)

# Draw the first Hey Muse test screen
with canvas(display) as draw:
    draw.rectangle((0, 0, 127, 63), outline="white")
    draw.text((34, 8), "HEY MUSE", fill="white")
    draw.line((10, 23, 117, 23), fill="white")
    draw.text((13, 30), "Raspberry Pi 3", fill="white")
    draw.text((22, 45), "OLED TEST OK", fill="white")

print("Display initialised!")
print("HEY MUSE should be visible on the OLED.")
print("Keeping test active for 30 seconds...")

time.sleep(30)
print("Test complete.")
