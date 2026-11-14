#!/usr/bin/env python3
"""Hey Muse Pi Phase 2a: OLED menu + e-paper + authenticated LAN reply inbox.

Known working hardware (from Phase 1):
  OLED SH1106: SPI0 CE0, DC=BCM24, RST=BCM25, rotate=180 degrees.
  e-paper 5.83-inch (C) v1: SPI0 CE1, DC=BCM22, RST=BCM17,
    BUSY=BCM27, rotate=180 degrees. epd5in83bc driver configured separately.
  Joystick: UP=6, DOWN=19, LEFT=5, RIGHT=26, SELECT=13.
  Buttons: KEY1=21, KEY2=20, KEY3=16.

No ESP32 firmware changes are made by this program. The Pi accepts HTTP text;
ESP32 will need a future sender patch to deliver real Muse replies.
"""

from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import socket
import subprocess
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from PIL import Image, ImageDraw, ImageFont

# These correspond to the user's tested physical mounting and wiring.
EPAPER_ROTATE_180 = True
OLED_ROTATE_180 = True
EPD_W, EPD_H = 600, 448
# Waveshare recommends 180 seconds for regular use. Set
# MUSE_EPAPER_REFRESH_SECONDS=30 only for short supervised navigation tests.
MIN_REFRESH_SECONDS = max(30, int(os.environ.get("MUSE_EPAPER_REFRESH_SECONDS", "180")))
MAX_POST_BYTES = 32 * 1024
MAX_REPLY_CHARS = 12000
MAX_HISTORY = 30

BUTTON_PINS = {
    "UP": 6, "DOWN": 19, "LEFT": 5, "RIGHT": 26,
    "SELECT": 13, "KEY1": 21, "KEY2": 20, "KEY3": 16,
}
MENU = ["Latest reply", "Older reply", "Demo reply", "Pi status", "Refresh", "Exit"]
DEMO_REPLY = (
    "Hey Muse Pi Phase 2 is ready. The OLED and the yellow, black and white "
    "e-paper now share a Raspberry Pi 3B. A protected HTTP endpoint can receive "
    "real AI response text over your home network. Next we will connect the "
    "ESP32's completed Muse-response event to this endpoint."
)


def project_dir() -> Path:
    return Path.home() / "hey-muse-display"


def config_dir() -> Path:
    return Path.home() / ".config" / "hey-muse-pi"


def token_path() -> Path:
    return config_dir() / "bridge_token"


def create_token_if_needed() -> str:
    """Return a local secret; never print it or place it in source control."""
    supplied = os.environ.get("MUSE_PI_TOKEN", "")
    if supplied:
        if len(supplied) < 24:
            raise ValueError("MUSE_PI_TOKEN must have at least 24 characters")
        return supplied
    base = config_dir()
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(base, 0o700)
    path = token_path()
    if not path.exists():
        # Exclusive creation prevents replacing an existing token accidentally.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(secrets.token_urlsafe(32) + "\n")
    os.chmod(path, 0o600)
    return path.read_text(encoding="utf-8").strip()


def status_info() -> str:
    try:
        disk = shutil.disk_usage("/")
        thermal = Path("/sys/class/thermal/thermal_zone0/temp")
        temp = f"{int(thermal.read_text()) / 1000:.1f} C" if thermal.exists() else "N/A"
        try:
            power = subprocess.run(
                ["vcgencmd", "get_throttled"], capture_output=True,
                text=True, timeout=3, check=False,
            ).stdout.strip() or "unknown"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            power = "unknown"
        return (
            f"Host: {socket.gethostname()}\n"
            f"Temperature: {temp}\n"
            f"Free storage: {disk.free / (1024**3):.1f} GB\n"
            f"Power: {power}\n"
            "OLED: SPI0 CE0\nE-paper: SPI0 CE1\n"
            "Muse bridge: HTTP inbox active"
        )
    except OSError as exc:
        return f"System status unavailable: {exc}"


# MUSE_COMPACT_EPAPER_V1
from functools import lru_cache

# E-paper content profiles, designed for the actual 600x448 panel.
EPAPER_BODY_SIZE = 18
EPAPER_LINE_PITCH = 23
EPAPER_MARGIN_X = 16
EPAPER_FOOTER_Y = EPD_H - 21

# Character hints select region-specific glyph shapes where possible.
# Most Han characters overlap between Chinese variants, so automatic detection
# is necessarily approximate. Japanese kana takes precedence.
_SIMPLIFIED_HINTS = set("这们国为个会发时对话说机电应进过现实问题学书东车门风马鱼鸟语体测显简听变开关点网")
_TRADITIONAL_HINTS = set("這們國為個會發時對話說機電應進過現實問題學書東車門風馬魚鳥語體測顯簡聽變開關點網")


def _text_region(text):
    if any(('\u3040' <= c <= '\u30ff') for c in text):
        return 'ja'
    simple = sum(ch in _SIMPLIFIED_HINTS for ch in text)
    trad = sum(ch in _TRADITIONAL_HINTS for ch in text)
    return 'zh-cn' if simple > trad else 'zh-tw'


@lru_cache(maxsize=48)
def load_font(size: int, bold: bool = False, lang: str = 'zh-tw') -> ImageFont.ImageFont:
    """Use the fontconfig-selected CJK font and its proper TTC face index."""
    style = 'Bold' if bold else 'Regular'
    families = [f'Noto Sans CJK {"JP" if lang == "ja" else "SC" if lang == "zh-cn" else "TC"}:style={style}',
                f'Droid Sans Fallback:lang={lang}']
    for family in families:
        try:
            result = subprocess.run(
                ['fc-match', '-f', '%{file}|%{index}\n', family],
                capture_output=True, text=True, check=True, timeout=3)
            path, idx = result.stdout.strip().split('|', 1)
            if Path(path).exists():
                return ImageFont.truetype(path, size, index=int(idx or 0))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def wrap_lines(text: str, draw: ImageDraw.ImageDraw, font, max_width: int) -> list[str]:
    """Pixel-aware Unicode wrapping. Never cut UTF-8 bytes or lose Han characters."""
    out = []
    for paragraph in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if not paragraph:
            out.append('')
            continue
        current = ''
        for ch in paragraph:
            trial = current + ch
            if current and draw.textlength(trial, font=font) > max_width:
                # Prefer a space break for English without harming unspaced CJK.
                split_at = current.rfind(' ')
                if split_at > 0 and split_at >= len(current) // 2:
                    out.append(current[:split_at].rstrip())
                    current = current[split_at+1:] + ch
                else:
                    out.append(current.rstrip())
                    current = ch.lstrip() if ch.isspace() else ch
            else:
                current = trial
        if current:
            out.append(current.rstrip())
    return out


def _page_geometry(heading: str, font_size: int):
    response = heading.upper() == 'AI RESPONSE'
    top = 15 if response else 53
    bottom = EPAPER_FOOTER_Y - 9
    pitch = max(21, int(round(font_size * 1.26)))
    count = max(1, (bottom - top) // pitch)
    return top, pitch, count


def paginate(text: str, font_size: int = EPAPER_BODY_SIZE,
             heading: str = 'AI RESPONSE') -> list[list[str]]:
    img = Image.new('1', (EPD_W, EPD_H), 255)
    draw = ImageDraw.Draw(img)
    font = load_font(font_size, lang=_text_region(text))
    lines = wrap_lines(text, draw, font, EPD_W - 2 * EPAPER_MARGIN_X)
    _, _, page_size = _page_geometry(heading, font_size)
    return [lines[i:i + page_size] for i in range(0, len(lines), page_size)] or [['(empty)']]


def build_image(text: str, heading: str, page: int, stamp: str = ''):
    """Dense, high-contrast layout; no HEY MUSE title on AI response pages."""
    font_size = EPAPER_BODY_SIZE
    pages = paginate(text, font_size, heading)
    page = max(0, min(page, len(pages)-1))
    black = Image.new('1', (EPD_W, EPD_H), 255)
    yellow = Image.new('1', (EPD_W, EPD_H), 255)
    b = ImageDraw.Draw(black)
    y = ImageDraw.Draw(yellow)
    is_response = heading.upper() == 'AI RESPONSE'
    if not is_response:
        # Small yellow accent, reduced from 49px to 5px.
        y.rectangle((0, 0, EPD_W-1, 4), fill=0)
        b.text((EPAPER_MARGIN_X, 15), heading[:38],
               font=load_font(19, True), fill=0)
        b.line((EPAPER_MARGIN_X, 43, EPD_W-EPAPER_MARGIN_X, 43), fill=0)
    top, pitch, _ = _page_geometry(heading, font_size)
    font = load_font(font_size, lang=_text_region(text))
    for i, line in enumerate(pages[page]):
        b.text((EPAPER_MARGIN_X, top + i*pitch), line, font=font, fill=0)
    b.line((EPAPER_MARGIN_X, EPAPER_FOOTER_Y - 5,
            EPD_W - EPAPER_MARGIN_X, EPAPER_FOOTER_Y - 5), fill=0)
    # Discreet metadata, no large page furniture.
    small = load_font(12)
    if stamp:
        b.text((EPAPER_MARGIN_X, EPAPER_FOOTER_Y), stamp[:42], font=small, fill=0)
    count_text = f'{page+1}/{len(pages)}'
    right = b.textbbox((0,0), count_text, font=small)[2]
    b.text((EPD_W - EPAPER_MARGIN_X - right, EPAPER_FOOTER_Y),
           count_text, font=small, fill=0)
    return black, yellow, len(pages)


def save_preview(directory: Path):
    """Generate test PNG files without importing drivers or opening GPIO."""
    directory.mkdir(parents=True, exist_ok=True)
    specimens = [
        ('preview_reply.png', DEMO_REPLY, 'AI RESPONSE'),
        ('preview_status.png', status_info(), 'PI STATUS'),
        ('preview_traditional_chinese.png',
         '香港是一個充滿活力的國際城市，融合了東西方文化，並擁有豐富的歷史與美食。\\n'
         '人工智能可以理解自然語言、協助程式設計，以及回答日常生活中的問題。\\n'
         '請以繁體中文回答，並保持標點符號清楚易讀。', 'AI RESPONSE'),
        ('preview_simplified_chinese.png',
         '人工智能正在改变我们的生活方式，为教育、医疗和科技发展带来新的机遇。\\n'
         '请用简体中文回答，并展示多行文字、数字123和常见标点符号。', 'AI RESPONSE'),
        ('preview_japanese.png',
         '人工知能は、私たちの生活をより便利にするために、さまざまな分野で活用されています。\\n'
         'こんにちは。日本語のひらがな、カタカナ、漢字を正しく表示できるか確認します。', 'AI RESPONSE'),
        ('preview_mixed_languages.png',
         'Hey Muse 可以使用繁體中文、简体中文 and 日本語 in one reply.\\n'
         'こんにちは！你好！Hello! 12345', 'AI RESPONSE'),
    ]
    for name, text, heading in specimens:
        text = text.replace('\\n', '\n')
        black, yellow, page_count = build_image(text, heading, 0, 'PREVIEW ONLY')
        rgb = Image.new('RGB', (EPD_W, EPD_H), 'white')
        rgb.paste((228,198,45), (0,0,EPD_W,EPD_H),
                  Image.eval(yellow.convert('L'), lambda value: 255-value))
        rgb.paste((0,0,0), (0,0,EPD_W,EPD_H),
                  Image.eval(black.convert('L'), lambda value: 255-value))
        rgb.save(directory / name)
        print(f'Saved {directory / name} ({page_count} page(s))')











class Inbox:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.history_file = self.directory / "conversation_history.jsonl"
        self.state_file = self.directory / "refresh_state.json"
        self.messages = deque(maxlen=MAX_HISTORY)
        self.queue = queue.Queue(maxsize=32)
        self.last_refresh = 0.0
        if self.history_file.exists():
            try:
                for line in self.history_file.read_text(encoding="utf-8").splitlines()[-MAX_HISTORY:]:
                    row = json.loads(line)
                    if isinstance(row.get("text"), str):
                        self.messages.append(row)
            except (OSError, ValueError, KeyError) as exc:
                print("Warning: cannot load earlier replies:", exc)
        if self.state_file.exists():
            try:
                self.last_refresh = float(json.loads(self.state_file.read_text())["last_refresh"])
            except (OSError, ValueError, KeyError, TypeError):
                pass

    def accept(self, row: dict):
        self.queue.put_nowait(row)

    def collect(self) -> int:
        count = 0
        while True:
            try:
                row = self.queue.get_nowait()
            except queue.Empty:
                break
            self.messages.append(row)
            count += 1
        if count:
            # Rewrite a bounded history atomically; don't dump private text into logs.
            payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in self.messages)
            temp = self.history_file.with_suffix(".tmp")
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(temp, self.history_file)
        return count

    def update_refresh_time(self):
        self.last_refresh = time.time()
        temp = self.state_file.with_suffix(".tmp")
        temp.write_text(json.dumps({"last_refresh": self.last_refresh}), encoding="utf-8")
        os.chmod(temp, 0o600)
        os.replace(temp, self.state_file)

    def remaining(self) -> int:
        return max(0, int(MIN_REFRESH_SECONDS - (time.time() - self.last_refresh) + 0.999))


class Handler(BaseHTTPRequestHandler):
    server_version = "HeyMusePiBridge/2.0"

    def log_message(self, fmt, *args):
        # Don't log conversation content or access tokens.
        print("[bridge]", self.address_string(), fmt % args, flush=True)

    def respond(self, status: int, payload: dict):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def authorised(self) -> bool:
        auth = self.headers.get("Authorization", "")
        expected = "Bearer " + self.server.token
        return hmac.compare_digest(auth, expected)

    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {"status": "ok", "service": "hey-muse-pi-bridge"})
        else:
            self.respond(404, {"error": "not_found"})

    def do_POST(self):
        # MUSE_LIVE_STATUS_PATCH_V1: reply + authenticated live-status endpoints.
        if self.path not in ("/api/v1/reply", "/api/v1/status"):
            self.respond(404, {"error": "not_found"})
            return
        if not self.authorised():
            self.respond(401, {"error": "unauthorised"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = -1
        if size <= 0 or size > MAX_POST_BYTES:
            self.respond(413, {"error": "invalid_payload_length"})
            return
        try:
            body = self.rfile.read(size)
            obj = json.loads(body.decode("utf-8"))
        except (UnicodeError, ValueError, TypeError):
            self.respond(400, {"error": "invalid_json"})
            return
        if not isinstance(obj, dict):
            self.respond(400, {"error": "expected_object"})
            return
        if self.path == "/api/v1/status":
            state = obj.get("state")
            if not isinstance(state, str) or state not in ("idle", "listening", "thinking", "speaking", "error"):
                self.respond(422, {"error": "invalid_state"})
                return
            # Queue newest status without blocking the HTTP server thread.
            try:
                self.server.status_queue.put_nowait(state)
            except queue.Full:
                try:
                    self.server.status_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self.server.status_queue.put_nowait(state)
                except queue.Full:
                    pass
            self.respond(202, {"accepted": True})
            return

        value = obj.get("text")
        if not isinstance(value, str) or not value.strip() or len(value) > MAX_REPLY_CHARS:
            self.respond(422, {"error": "invalid_text"})
            return
        source = obj.get("source", "esp32")
        if not isinstance(source, str) or len(source) > 40:
            source = "esp32"
        row = {"text": value.strip(), "source": source,
               "time": datetime.now().astimezone().isoformat(timespec="seconds")}
        try:
            self.server.inbox.accept(row)
        except queue.Full:
            self.respond(503, {"error": "inbox_full"})
            return
        self.respond(202, {"accepted": True})


class BridgeServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, token: str, inbox: Inbox):
        super().__init__(address, Handler)
        self.token = token
        self.inbox = inbox
        self.status_queue = queue.Queue(maxsize=32)


def start_server(bind: str, port: int, inbox: Inbox):
    token = create_token_if_needed()
    srv = BridgeServer((bind, port), token, inbox)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    print(f"Bridge listening on {bind}:{port}; POST /api/v1/reply (token required)")
    print("Token stored locally; never paste it into chat or firmware source control.")
    return srv


def send_test(port: int, token: str):
    payload = json.dumps({"source": "test", "text":
        "Hello from the Raspberry Pi network test. This text reached the "
        "Hey Muse companion through its authenticated local HTTP API. "
        "The ESP32 will send actual Muse replies in the next step."}).encode("utf-8")
    req = Request(f"http://127.0.0.1:{port}/api/v1/reply", data=payload,
                  headers={"Authorization": "Bearer " + token,
                           "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=5) as response:
            print("Bridge response:", response.status, response.read().decode())
    except HTTPError as exc:
        print("Bridge error:", exc.code, exc.read().decode())


def run_server_only(inbox: Inbox, bind: str, port: int):
    server = start_server(bind, port, inbox)
    print("Headless test mode. Ctrl+C stops. No hardware display access.")
    try:
        while True:
            count = inbox.collect()
            if count:
                print(f"Saved {count} new response(s); total retained: {len(inbox.messages)}")
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


def run_app(inbox: Inbox, bind: str, port: int):
    from gpiozero import Button
    from concurrent.futures import ThreadPoolExecutor
    from luma.core.interface.serial import spi
    from luma.core.render import canvas
    from luma.oled.device import sh1106
    from waveshare_epd import epd5in83bc

    serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=2000000)
    oled = sh1106(serial, width=128, height=64, rotate=2 if OLED_ROTATE_180 else 0)
    oled.contrast(255)
    buttons = {name: Button(pin, pull_up=True, bounce_time=0.05)
               for name, pin in BUTTON_PINS.items()}
    previous = {name: btn.is_pressed for name, btn in buttons.items()}
    server = start_server(bind, port, inbox)

    selected = 0
    view = "demo"
    page = 0
    history_index = -1  # -1 means the newest saved reply
    message = "Ready"
    last_redraw = 0.0
    new_reply = False
    live_status = "idle"
    live_status_at = time.monotonic()
    # Expire stale transient statuses if Wi-Fi drops or ESP32 reboots.
    LIVE_STATUS_TIMEOUT = 90.0
    # AUTO_EPAPER_REFRESH_PATCH_V1: pending latest reply, handled in the main loop.
    pending_auto_refresh = False
    # Manual page changes should survive both the cooldown and a busy panel.
    # While waiting, the most recent selection wins.
    pending_manual_refresh = False
    # MUSE_ASYNC_EPAPER_PATCH_V1: one e-paper job at a time, never draw OLED in worker.
    epaper_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="muse_epaper")
    epaper_future = None
    epaper_job_latest = False

    def current():
        if view == "status":
            return status_info(), "PI STATUS", "RASPBERRY PI"
        if view == "reply":
            if not inbox.messages:
                return "No AI replies received yet.", "AI RESPONSE", "INBOX EMPTY"
            item = list(inbox.messages)[history_index]
            return item["text"], "AI RESPONSE", item.get("time", "")[:19]
        return DEMO_REPLY, "DEMO RESPONSE", "SAMPLE ONLY"

    def draw_oled():
        with canvas(oled) as draw:
            draw.rectangle((0, 0, 127, 63), outline="white")
            draw.text((32, 2), "HEY MUSE", fill="white")
            draw.line((4, 16, 123, 16), fill="white")
            draw.text((4, 19), "> " + MENU[selected], fill="white")
            text, heading, _ = current()
            pages = paginate(text, heading=heading)
            if view == "reply":
                subtitle = f"Reply {len(inbox.messages)} | {page + 1}/{len(pages)}"
            else:
                subtitle = f"{view} | {page + 1}/{len(pages)}"
            if pending_manual_refresh:
                subtitle += " Q"
            draw.text((4, 33), subtitle[:21], fill="white")
            # Status line is independent of manual menu and e-paper view.
            if live_status != "idle":
                status = "MUSE: " + live_status.upper()
            else:
                status = ("NEW REPLY - KEY2" if new_reply else "MUSE: READY")
            draw.text((4, 47), status[:20], fill="white")

    def epaper_job(black, yellow):
        """Hardware operations only. GPIO objects remain within this one process.

        The OLED uses SPI0/CE0 and e-paper SPI0/CE1. Linux spidev serialises
        transfers. Never hold an application-wide SPI lock across ReadBusy().
        """
        epd = epd5in83bc.EPD()
        epd.init()
        epd.display(epd.getbuffer(black), epd.getbuffer(yellow))
        epd.sleep()

    def refresh(manual=True):
        nonlocal message, new_reply, pending_auto_refresh, pending_manual_refresh
        nonlocal epaper_future, epaper_job_latest
        if manual:
            # A button press updates the desired view/page immediately;
            # e-paper writes are deferred until it is safe to start a new one.
            pending_manual_refresh = True
        if epaper_future is not None:
            message = "Page queued (e-paper busy)" if manual else "E-paper busy"
            draw_oled()
            return False

        remaining = inbox.remaining()
        if remaining:
            message = f"Page queued ({remaining}s)" if manual else f"Wait {remaining}s"
            print("E-paper cooldown:", remaining, "seconds")
            draw_oled()
            return False

        # Snapshot selection and render in main thread. Worker never reads
        # mutable menu state or writes to the OLED.
        text, heading, stamp = current()
        black, yellow, _ = build_image(text, heading, page, stamp)
        if EPAPER_ROTATE_180:
            black = black.transpose(Image.Transpose.ROTATE_180)
            yellow = yellow.transpose(Image.Transpose.ROTATE_180)

        latest = view == "reply" and history_index == -1
        # Same safety policy as the original: persist the cooldown BEFORE I/O.
        inbox.update_refresh_time()
        message = "Updating e-paper"
        epaper_job_latest = latest
        if latest:
            # New replies received during this job will set pending True again.
            pending_auto_refresh = False
            new_reply = False
        try:
            epaper_future = epaper_executor.submit(epaper_job, black, yellow)
        except Exception:
            if latest:
                pending_auto_refresh = True
                new_reply = True
            message = "E-paper error"
            draw_oled()
            raise
        # The current selection is now represented by the submitted image.
        # Any subsequent button press can queue another selection.
        pending_manual_refresh = False
        print("E-paper refresh beginning (background operation)...", flush=True)
        draw_oled()
        return True

    def choose():
        nonlocal selected, view, page, history_index, message
        action = MENU[selected]
        if action == "Latest reply":
            if not inbox.messages:
                message = "No replies yet"
                return
            view, history_index, page = "reply", -1, 0
            refresh()
        elif action == "Older reply":
            if len(inbox.messages) < 2:
                message = "No older reply"
                return
            view = "reply"
            history_index = (history_index - 1) % len(inbox.messages)
            page = 0
            refresh()
        elif action == "Demo reply":
            view, page = "demo", 0
            refresh()
        elif action == "Pi status":
            view, page = "status", 0
            refresh()
        elif action == "Refresh":
            refresh()
        elif action == "Exit":
            raise StopIteration

    def move_page(delta: int):
        nonlocal page, message
        text, heading, _ = current()
        count = len(paginate(text, heading=heading))
        page = (page + delta) % count
        message = f"Page {page+1}/{count}"
        refresh()

    draw_oled()
    print("HEY MUSE PI PHASE 2 | OLED CE0 + E-PAPER CE1")
    print("UP/DOWN menu, SELECT activate, LEFT/RIGHT pages")
    print("KEY1 home, KEY2 latest reply, KEY3 previous page")
    print("New network replies auto-refresh when e-paper cooldown permits.")
    print(f"Ctrl+C to quit. Refresh cooldown: {MIN_REFRESH_SECONDS}s.")
    try:
        while True:
            # Complete finished e-paper job in the main thread; do not touch
            # OLED or mutable reply state from the background worker.
            if epaper_future is not None and epaper_future.done():
                completed = epaper_future
                epaper_future = None
                try:
                    completed.result()
                    message = "E-paper updated"
                    print("E-paper refresh completed", flush=True)
                except Exception as exc:
                    message = "E-paper error"
                    print(f"E-paper refresh failed: {exc!r}", flush=True)
                    if epaper_job_latest:
                        pending_auto_refresh = True
                        new_reply = True
                    # Existing persisted cooldown prevents rapid retries.
                epaper_job_latest = False
                draw_oled()

            # Read only the newest status. GPIO drawing stays on the main thread.
            newest_status = None
            while True:
                try:
                    newest_status = server.status_queue.get_nowait()
                except queue.Empty:
                    break
            if newest_status is not None:
                live_status = newest_status
                live_status_at = time.monotonic()
                draw_oled()
            elif live_status != "idle" and time.monotonic() - live_status_at > LIVE_STATUS_TIMEOUT:
                live_status = "idle"
                draw_oled()

            received = inbox.collect()
            if received:
                new_reply = True
                pending_auto_refresh = True
                message = f"Received {received} reply"
                print("Received", received, "reply(s), queued for automatic e-paper refresh")
                draw_oled()
            for name, btn in buttons.items():
                down = btn.is_pressed
                if down and not previous[name]:
                    if name == "UP":
                        selected = (selected - 1) % len(MENU)
                        message = "Select action"
                    elif name == "DOWN":
                        selected = (selected + 1) % len(MENU)
                        message = "Select action"
                    elif name == "KEY1":
                        selected = 0
                        message = "Home"
                    elif name in ("LEFT", "RIGHT", "KEY3"):
                        move_page(1 if name == "RIGHT" else -1)
                    elif name == "KEY2":
                        selected = 0
                        choose()
                    elif name == "SELECT":
                        choose()
                    draw_oled()
                previous[name] = down
            # Prioritise a button-selected page over auto-refresh. A page
            # requested during a busy job or cooldown must not be lost.
            if (pending_manual_refresh and epaper_future is None
                    and inbox.remaining() == 0):
                try:
                    refresh(manual=True)
                except Exception as exc:
                    print(f"Queued page refresh failed: {exc!r}", flush=True)
            # Automatic refresh only starts after any manual request is handled.
            elif (not pending_manual_refresh and pending_auto_refresh
                    and epaper_future is None and inbox.messages
                    and inbox.remaining() == 0):
                view, history_index, page = "reply", -1, 0
                print("Auto-refresh: showing the latest AI reply")
                try:
                    refresh(manual=False)
                except Exception as exc:
                    # refresh() persists its cooldown before accessing e-paper.
                    # Keep pending to retry after the cooldown; do not kill the UI.
                    print(f"Automatic e-paper refresh failed: {exc!r}", flush=True)
            if time.monotonic() - last_redraw > 1.0:
                last_redraw = time.monotonic()
            time.sleep(0.03)
    except (KeyboardInterrupt, StopIteration):
        print("Stopping Hey Muse Pi companion")
    finally:
        # Finish any active e-paper operation before closing display GPIOs.
        epaper_executor.shutdown(wait=True)
        server.shutdown()
        server.server_close()
        for btn in buttons.values():
            btn.close()
        try:
            oled.clear()
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser(description="Hey Muse Pi displays + local AI reply inbox")
    ap.add_argument("--preview", action="store_true", help="Render PNGs, no GPIO")
    ap.add_argument("--server-only", action="store_true", help="HTTP receiver without GPIO")
    ap.add_argument("--send-test", action="store_true", help="POST a test response to local server")
    ap.add_argument("--listen", default="127.0.0.1", help="Use 0.0.0.0 for trusted LAN access")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    if args.preview:
        save_preview(Path.cwd())
        return
    if args.send_test:
        send_test(args.port, create_token_if_needed())
        return
    inbox = Inbox(project_dir())
    if args.server_only:
        run_server_only(inbox, args.listen, args.port)
    else:
        run_app(inbox, args.listen, args.port)


if __name__ == "__main__":
    main()
