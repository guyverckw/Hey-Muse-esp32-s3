
from waveshare_epd import epd5in83bc
from PIL import Image, ImageDraw, ImageFont
import os

print("HEY MUSE - E-PAPER TEST", flush=True)

epd = epd5in83bc.EPD()

print(f"Display: {epd.width} x {epd.height}", flush=True)

# Create white backgrounds for both colour planes
black = Image.new("1", (epd.width, epd.height), 255)
accent = Image.new("1", (epd.width, epd.height), 255)

draw_black = ImageDraw.Draw(black)
draw_accent = ImageDraw.Draw(accent)

font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def load_font(size):
    if os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()

title_font = load_font(58)
body_font = load_font(25)
small_font = load_font(20)

# Header
draw_black.text((45, 35), "HEY MUSE", font=title_font, fill=0)
draw_black.line((40, 120, 560, 120), fill=0, width=4)

# Main message
draw_black.text(
    (45, 155),
    "Raspberry Pi 3",
    font=body_font,
    fill=0
)
draw_black.text(
    (45, 200),
    "E-Paper Test",
    font=body_font,
    fill=0
)

# Black test area
draw_black.rectangle((45, 285, 260, 345), fill=0)

# Third-colour test area (red or yellow, depending on panel)
draw_accent.rectangle((340, 285, 555, 345), fill=0)

draw_black.text(
    (45, 385),
    "Display test complete",
    font=small_font,
    fill=0
)

print("Initialising display...", flush=True)
epd.init()

print("Sending image and refreshing...", flush=True)
epd.display(
    epd.getbuffer(black),
    epd.getbuffer(accent)
)

print("Image displayed.", flush=True)

# Enter low-power mode while preserving the displayed image
epd.sleep()

print("Test completed successfully.", flush=True)
