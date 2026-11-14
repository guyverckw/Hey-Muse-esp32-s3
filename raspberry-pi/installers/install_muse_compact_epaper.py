#!/usr/bin/env python3
"""Patch Hey Muse Pi e-paper formatting; preview multilingual layout without GPIO.

Run on Raspberry Pi from ~/hey-muse-display:
    python3 install_muse_compact_epaper.py --dry-run
    python3 install_muse_compact_epaper.py
    python3 muse_pi.py --preview
"""
import argparse
import ast
import difflib
import py_compile
import shutil
from datetime import datetime
from pathlib import Path

MARKER = '# MUSE_COMPACT_EPAPER_V1'
REPLACEMENTS = r'''# MUSE_COMPACT_EPAPER_V1
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
'''

# Replace AST-identified top-level functions; ensures source ranges don't drift.
NAMES = ('load_font', 'wrap_lines', 'paginate', 'build_image', 'save_preview')

def patch(source: str) -> str:
    if MARKER in source:
        raise RuntimeError('Compact layout already installed; no changes made')
    tree = ast.parse(source)
    found = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in NAMES}
    if set(found) != set(NAMES):
        raise RuntimeError(f'Missing expected functions: {sorted(set(NAMES)-set(found))}; no changes made')
    if not all(k in source for k in ('EPD_W, EPD_H = 600, 448', 'MIN_REFRESH_SECONDS = 180', 'def run_app(')):
        raise RuntimeError('Firmware script layout unexpected; no changes made')
    lines = source.splitlines(keepends=True)
    # Remove all five original functions and insert new equivalents before first.
    positions = [(found[n].lineno-1, found[n].end_lineno) for n in NAMES]
    first = min(start for start, _ in positions)
    for start, end in sorted(positions, reverse=True):
        del lines[start:end]
    lines[first:first] = [REPLACEMENTS + '\n']
    result = ''.join(lines)
    ast.parse(result)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--file', type=Path, default=Path.home()/'hey-muse-display'/'muse_pi.py')
    args = ap.parse_args()
    src = args.file.expanduser().resolve()
    before = src.read_text(encoding='utf-8')
    after = patch(before)
    if args.dry_run:
        print('PASS: expected functions found; patched Python syntax valid; no files changed.')
        diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile='before', tofile='proposed', lineterm=''))
        print('\n'.join(diff[:75]))
        print(f'... Diff lines: {len(diff)} (showing first 75)')
        return
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = src.with_name(f'{src.stem}.before_compact_{stamp}{src.suffix}')
    shutil.copy2(src, backup)
    temp = src.with_name(src.name+'.compact.tmp')
    try:
        temp.write_text(after, encoding='utf-8')
        temp.chmod(src.stat().st_mode & 0o777)
        py_compile.compile(str(temp), doraise=True)
        temp.replace(src)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    print('Installed. Backup:', backup)
    print('Next: python3 muse_pi.py --preview')
    print('Preview uses no GPIO. Physical display changes after restarting muse_pi.py.')

if __name__ == '__main__':
    main()
