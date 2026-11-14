
from luma.core.interface.serial import spi
from luma.oled.device import sh1106
from luma.core.render import canvas
from gpiozero import Button
import time

# ==========================================
# HEY MUSE - OLED + JOYSTICK + BUTTON TEST
# Waveshare 1.3-inch OLED HAT
# Raspberry Pi 3 Model B
# ==========================================

# GPIO numbers use BCM numbering
BUTTON_PINS = {
    "UP": 6,
    "DOWN": 19,
    "LEFT": 5,
    "RIGHT": 26,
    "PRESS": 13,
    "KEY1": 21,
    "KEY2": 20,
    "KEY3": 16,
}

print("Initialising OLED...")

# OLED SPI configuration - confirmed working
serial = spi(
    port=0,
    device=0,
    gpio_DC=24,
    gpio_RST=25,
    bus_speed_hz=2000000
)

display = sh1106(serial, width=128, height=64)
display.contrast(255)

print("Initialising joystick and buttons...")

buttons = {
    name: Button(pin, pull_up=True, bounce_time=0.05)
    for name, pin in BUTTON_PINS.items()
}

# Track how many times a control was pressed
press_count = 0


def show_button(name, count):
    """Update OLED with the last button pressed."""

    with canvas(display) as draw:

        # Outer border
        draw.rectangle(
            (0, 0, 127, 63),
            outline="white"
        )

        # Header
        draw.text((37, 3), "HEY MUSE", fill="white")
        draw.line(
            (5, 17, 122, 17),
            fill="white"
        )

        # Button status
        draw.text(
            (12, 21),
            "BUTTON PRESSED:",
            fill="white"
        )

        # Centre the button label approximately
        x = max(3, (128 - len(name) * 6) // 2)
        draw.text(
            (x, 34),
            name,
            fill="white"
        )

        # Counter
        draw.text(
            (12, 51),
            f"Total presses: {count}",
            fill="white"
        )


def show_welcome():
    """Show initial screen."""
    with canvas(display) as draw:
        draw.rectangle(
            (0, 0, 127, 63),
            outline="white"
        )
        draw.text((37, 5), "HEY MUSE", fill="white")
        draw.line((5, 20, 122, 20), fill="white")
        draw.text((16, 29), "BUTTON TEST", fill="white")
        draw.text((12, 46), "Press a control", fill="white")


show_welcome()

# Remember previous state of each button
previous = {
    name: button.is_pressed
    for name, button in buttons.items()
}

print()
print("================================")
print(" HEY MUSE INTERACTIVE OLED TEST")
print("================================")
print("Move the joystick or press KEY1-3.")
print("The OLED will display the control.")
print("Press Ctrl+C to exit.")
print()

try:
    while True:

        for name, button in buttons.items():

            currently_pressed = button.is_pressed

            # Detect a new press, not a held button
            if currently_pressed and not previous[name]:

                press_count += 1

                print(
                    f"[{press_count}] Pressed: {name}",
                    flush=True
                )

                # Update the OLED
                show_button(name, press_count)

            previous[name] = currently_pressed

        # Small delay prevents excessive CPU usage
        time.sleep(0.02)

except KeyboardInterrupt:
    print("\nTest stopped.")

finally:
    for button in buttons.values():
        button.close()
    print("GPIO resources released.")
