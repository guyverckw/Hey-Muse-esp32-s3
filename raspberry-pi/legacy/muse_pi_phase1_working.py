#!/usr/bin/env python3
"""Hey Muse Raspberry Pi companion, Phase 1.

Hardware previously validated by the user:
  Waveshare 1.3-inch OLED HAT: SH1106, SPI0 CE0, DC=BCM24, RST=BCM25.
  Waveshare old 5.83-inch e-Paper (C): 600x448, epd5in83bc,
      SPI0 CE1, DC=BCM22, RST=BCM17, BUSY=BCM27.
  Joystick and keys use the original Waveshare OLED HAT connections.

No ESP32 connection is attempted by this prototype.
"""

import argparse
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

EPD_W = 600
EPD_H = 448

# Display mounting orientation: change these independently if needed.
EPAPER_ROTATE_180 = True   # Rotate both e-paper colour planes before sending
OLED_ROTATE_180 = True    # Rotate OLED by 180 degrees (matches physical mounting)
MIN_EPD_REFRESH_SECONDS = 180  # Vendor advises >= 180 seconds between refreshes

BUTTON_PINS = {
    "UP": 6,
    "DOWN": 19,
    "LEFT": 5,
    "RIGHT": 26,
    "SELECT": 13,
    "KEY1": 21,
    "KEY2": 20,
    "KEY3": 16,
}

MENU = ["Demo reply", "Pi status", "Next page", "Prev page", "Refresh", "Exit"]

DEMO_PAGES = [
    (
        "MUSE RESPONSE",
        "Hello! This is a sample reply from the Hey Muse companion. "
        "The Raspberry Pi is now connected to a small OLED menu and a "
        "larger black, white and yellow e-paper screen. "
        "The response shown here is demonstration text only; the ESP32 "
        "has not sent any conversation data yet.",
    ),
    (
        "MUSE RESPONSE",
        "The OLED joystick can be used to select which answer to read. "
        "The e-paper holds its image without continuous updates, making "
        "it useful for long answers, instructions and daily summaries. "
        "In a later phase we can deliver completed Muse responses from the "
        "ESP32-S3 over your home Wi-Fi network.",
    ),
    (
        "MUSE RESPONSE",
        "A note about this particular three-colour display: it refreshes "
        "slowly. This prototype keeps at least three minutes between "
        "refreshes, as recommended for this e-paper family. "
        "You can navigate the OLED menu at any time, but selecting a new "
        "e-paper page may require waiting before refreshing.",
    ),
]


def font(size, bold=False):
    base = "/usr/share/fonts/truetype/dejavu/"
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(base + filename, size)
    except OSError:
        return ImageFont.load_default()


def pi_status_text():
    try:
        hostname = socket.gethostname()
        disk = shutil.disk_usage("/")
        free_gb = disk.free / (1024 ** 3)
        temp_path = Path("/sys/class/thermal/thermal_zone0/temp")
        temperature = f"{int(temp_path.read_text()) / 1000:.1f} C" if temp_path.exists() else "N/A"
        try:
            throttled = subprocess.run(
                ["vcgencmd", "get_throttled"],
                capture_output=True, text=True, timeout=3, check=False,
            ).stdout.strip() or "N/A"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            throttled = "N/A"
        return (
            "Host: " + hostname + "\n"
            "System: Raspberry Pi 3B\n"
            "CPU temperature: " + temperature + "\n"
            f"Free storage: {free_gb:.1f} GB\n"
            "Power status: " + throttled + "\n"
            "Interface: OLED CE0 / E-paper CE1\n"
            "Hey Muse connection: not configured"
        )
    except Exception as exc:
        return f"Unable to read status: {exc}"


def wrap_text(draw, paragraph, fnt, max_width):
    """Wrap text to the e-paper pixel width, preserving explicit newlines."""
    lines = []
    for part in paragraph.split("\n"):
        if not part.strip():
            lines.append("")
            continue
        current = ""
        for word in part.split():
            candidate = word if not current else current + " " + word
            if draw.textlength(candidate, font=fnt) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def make_epaper_images(view, page):
    """Create bitmaps for two colour planes; no hardware access here."""
    black = Image.new("1", (EPD_W, EPD_H), 255)
    yellow = Image.new("1", (EPD_W, EPD_H), 255)
    b = ImageDraw.Draw(black)
    y = ImageDraw.Draw(yellow)
    f_heading = font(35, bold=True)
    f_sub = font(23, bold=True)
    f_body = font(22)
    f_footer = font(17)

    y.rectangle((0, 0, EPD_W - 1, 42), fill=0)
    b.text((32, 57), "HEY MUSE", font=f_heading, fill=0)
    b.line((30, 111, EPD_W - 30, 111), fill=0, width=3)

    if view == "status":
        title, content, number, total = "RASPBERRY PI STATUS", pi_status_text(), 1, 1
    else:
        number = page % len(DEMO_PAGES) + 1
        total = len(DEMO_PAGES)
        title, content = DEMO_PAGES[number - 1]

    b.text((32, 124), title, font=f_sub, fill=0)
    vertical = 167
    for line in wrap_text(b, content, f_body, EPD_W - 64):
        if vertical + 28 > EPD_H - 48:
            b.text((32, EPD_H - 69), "...", font=f_body, fill=0)
            break
        b.text((32, vertical), line, font=f_body, fill=0)
        vertical += 31 if line else 18

    b.line((30, EPD_H - 42, EPD_W - 30, EPD_H - 42), fill=0, width=2)
    b.text((32, EPD_H - 35), "DEMO ONLY - NO LIVE AI LINK", font=f_footer, fill=0)
    b.text((EPD_W - 116, EPD_H - 35), f"{number} / {total}", font=f_footer, fill=0)
    return black, yellow


def save_previews(folder):
    folder.mkdir(parents=True, exist_ok=True)
    for view, page, filename in [
        ("demo", 0, "preview_demo.png"),
        ("status", 0, "preview_status.png"),
    ]:
        black, yellow = make_epaper_images(view, page)
        result = Image.new("RGB", (EPD_W, EPD_H), "white")
        yellow_mask = Image.eval(yellow.convert("L"), lambda v: 255 - v)
        black_mask = Image.eval(black.convert("L"), lambda v: 255 - v)
        result.paste((223, 193, 30), (0, 0, EPD_W, EPD_H), yellow_mask)
        result.paste((0, 0, 0), (0, 0, EPD_W, EPD_H), black_mask)
        result.save(folder / filename)
        print("Wrote", folder / filename)


def run():
    from gpiozero import Button
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    from waveshare_epd import epd5in83bc

    serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=2000000)
    oled = sh1106(serial, width=128, height=64,
                 rotate=2 if OLED_ROTATE_180 else 0)
    oled.contrast(255)
    buttons = {
        name: Button(pin, pull_up=True, bounce_time=0.05)
        for name, pin in BUTTON_PINS.items()
    }
    previous = {name: obj.is_pressed for name, obj in buttons.items()}

    selected = 0
    view = "demo"
    page = 0
    last_refresh = -1e12
    message = "Ready - select item"

    def oled_draw():
        with canvas(oled) as draw:
            draw.rectangle((0, 0, 127, 63), outline="white")
            draw.text((32, 2), "HEY MUSE", fill="white")
            draw.line((4, 16, 123, 16), fill="white")
            draw.text((4, 20), "> " + MENU[selected], fill="white")
            if view == "demo":
                draw.text((4, 34), f"Demo page {page + 1}/{len(DEMO_PAGES)}", fill="white")
            else:
                draw.text((4, 34), "Pi status mode", fill="white")
            draw.text((4, 48), message[:20], fill="white")

    def refresh():
        nonlocal last_refresh, message
        remain = MIN_EPD_REFRESH_SECONDS - (time.monotonic() - last_refresh)
        if remain > 0:
            message = f"Wait {int(remain) + 1}s"
            print(f"E-paper cooldown: {remain:.0f} seconds remaining")
            oled_draw()
            return
        message = "E-paper refreshing"
        oled_draw()
        print("Updating e-paper ... this takes several tens of seconds")
        epd = None
        try:
            black, yellow = make_epaper_images(view, page)
            if EPAPER_ROTATE_180:
                black = black.transpose(Image.Transpose.ROTATE_180)
                yellow = yellow.transpose(Image.Transpose.ROTATE_180)
            epd = epd5in83bc.EPD()
            epd.init()
            epd.display(epd.getbuffer(black), epd.getbuffer(yellow))
            last_refresh = time.monotonic()
            epd.sleep()
            message = "E-paper updated"
            print("E-paper updated; sleeping")
        except Exception as exc:
            message = "E-paper error"
            print("E-paper error:", repr(exc))
            print("Do not repeatedly retry if refresh is stuck; check output")
            # Re-raise so a hardware/driver fault is not concealed.
            raise
        finally:
            oled_draw()

    def change_page(offset):
        nonlocal page, view, message
        if view != "demo":
            view = "demo"
        page = (page + offset) % len(DEMO_PAGES)
        message = "Page selected"
        oled_draw()
        refresh()

    oled_draw()
    print("HEY MUSE PI PHASE 1 - OLED menu and e-paper reader")
    print("UP/DOWN: menu | SELECT: activate | LEFT/RIGHT: pages")
    print("KEY1: menu home | KEY2: refresh | KEY3: previous page")
    print("Press Ctrl+C to quit. E-paper has a 180-second refresh limit.")

    try:
        while True:
            for name, btn in buttons.items():
                pressed = btn.is_pressed
                if pressed and not previous[name]:
                    print("Pressed", name)
                    if name == "UP":
                        selected = (selected - 1) % len(MENU)
                        message = "Choose menu item"
                        oled_draw()
                    elif name == "DOWN":
                        selected = (selected + 1) % len(MENU)
                        message = "Choose menu item"
                        oled_draw()
                    elif name == "KEY1":
                        selected = 0
                        message = "Main menu"
                        oled_draw()
                    elif name in ("RIGHT", "LEFT", "KEY3"):
                        change_page(1 if name == "RIGHT" else -1)
                    elif name == "KEY2":
                        refresh()
                    elif name == "SELECT":
                        action = MENU[selected]
                        if action == "Demo reply":
                            view, page = "demo", 0
                            refresh()
                        elif action == "Pi status":
                            view, page = "status", 0
                            refresh()
                        elif action == "Next page":
                            change_page(1)
                        elif action == "Prev page":
                            change_page(-1)
                        elif action == "Refresh":
                            refresh()
                        elif action == "Exit":
                            return
                previous[name] = pressed
            time.sleep(0.03)
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        for btn in buttons.values():
            btn.close()
        try:
            oled.clear()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Hey Muse Pi OLED + e-paper prototype")
    parser.add_argument("--preview", action="store_true",
                        help="Generate preview PNGs without accessing GPIO")
    args = parser.parse_args()
    if args.preview:
        save_previews(Path.cwd())
    else:
        run()


if __name__ == "__main__":
    main()
