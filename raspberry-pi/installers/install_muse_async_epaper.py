#!/usr/bin/env python3
"""Phase 3d: run Hey Muse Pi e-paper refresh in a single background worker.

Preserves live OLED status, authenticated HTTP endpoints, manual controls and
180-second refresh cooldown. Does not touch ESP32 or Waveshare driver files.

Usage on Raspberry Pi:
    python3 install_muse_async_epaper.py --dry-run
    python3 install_muse_async_epaper.py
"""
import argparse
import ast
from datetime import datetime
import difflib
from pathlib import Path
import shutil
import sys

MARKER = 'MUSE_ASYNC_EPAPER_PATCH_V1'


def replace_once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise ValueError(f'{label}: expected exactly one match, found {n}')
    return src.replace(old, new, 1)


def patch(src):
    if MARKER in src:
        raise ValueError('Async e-paper patch already installed; no changes needed')
    if 'AUTO_EPAPER_REFRESH_PATCH_V1' not in src or 'MUSE_LIVE_STATUS_PATCH_V1' not in src:
        raise ValueError('Expected both working Phase 2 auto-refresh and Phase 3 live-status patches')

    src = replace_once(src,
        '    from gpiozero import Button\n',
        '    from gpiozero import Button\n    from concurrent.futures import ThreadPoolExecutor\n',
        'import background worker')
    src = replace_once(src,
        '    pending_auto_refresh = False\n\n    def current():',
        '''    pending_auto_refresh = False
    # MUSE_ASYNC_EPAPER_PATCH_V1: one e-paper job at a time, never draw OLED in worker.
    epaper_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="muse_epaper")
    epaper_future = None
    epaper_job_latest = False

    def current():''',
        'create worker state')

    start = '    def refresh():\n'
    end = '    def choose():\n'
    if src.count(start) != 1 or src.count(end) != 1:
        raise ValueError('Could not uniquely locate original refresh() method')
    a = src.index(start)
    b = src.index(end, a)
    original_refresh = src[a:b]
    for expected in ('epd = epd5in83bc.EPD()', 'inbox.update_refresh_time()',
                     'epd.display(epd.getbuffer(black), epd.getbuffer(yellow))',
                     'black = black.transpose(Image.Transpose.ROTATE_180)',
                     'def refresh():', 'pending_auto_refresh'):
        if expected not in original_refresh:
            raise ValueError('Original refresh() changed; missing ' + expected)

    replacement = '''    def epaper_job(black, yellow):
        """Hardware operations only. GPIO objects remain within this one process.

        The OLED uses SPI0/CE0 and e-paper SPI0/CE1. Linux spidev serialises
        transfers. Never hold an application-wide SPI lock across ReadBusy().
        """
        epd = epd5in83bc.EPD()
        epd.init()
        epd.display(epd.getbuffer(black), epd.getbuffer(yellow))
        epd.sleep()

    def refresh():
        nonlocal message, new_reply, pending_auto_refresh
        nonlocal epaper_future, epaper_job_latest
        # Manual requests while busy do not schedule an overlapping job.
        if epaper_future is not None:
            message = "E-paper busy"
            draw_oled()
            return False

        remaining = inbox.remaining()
        if remaining:
            message = f"Wait {remaining}s (KEY2)"
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
        print("E-paper refresh beginning (background operation)...", flush=True)
        draw_oled()
        return True

'''
    src = src[:a] + replacement + src[b:]

    src = replace_once(src,
        '        while True:\n            # Read only the newest status. GPIO drawing stays on the main thread.\n',
        '''        while True:
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
''',
        'poll e-paper worker without blocking status loop')

    src = replace_once(src,
        '''            # Refresh on the main thread only, respecting the existing 180s cooldown.
            # Multiple incoming replies collapse into the newest saved message.
            if pending_auto_refresh and inbox.messages and inbox.remaining() == 0:
''',
        '''            # Only schedule refresh from the main thread; hardware work
            # runs in the background. Latest reply wins after cooldown.
            if (pending_auto_refresh and epaper_future is None
                    and inbox.messages and inbox.remaining() == 0):
''',
        'adjust auto refresh scheduling')

    src = replace_once(src,
        '''    finally:
        server.shutdown()
''',
        '''    finally:
        # Finish any active e-paper operation before closing display GPIOs.
        epaper_executor.shutdown(wait=True)
        server.shutdown()
''',
        'order shutdown safely')

    ast.parse(src, filename='muse_pi.py')
    return src


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--file', type=Path, default=Path.home() / 'hey-muse-display' / 'muse_pi.py')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    path = args.file.expanduser().resolve()
    if not path.is_file():
        sys.exit(f'ERROR: File not found: {path}')
    old = path.read_text(encoding='utf-8')
    try:
        new = patch(old)
    except (ValueError, SyntaxError) as exc:
        sys.exit(f'ERROR: {exc}. No changes made.')
    if args.dry_run:
        print('PASS: patch anchors verified; proposed Python syntax valid. No files changed.\n')
        print(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                           fromfile='muse_pi.py (existing)',
                                           tofile='muse_pi.py (proposed)')))
        return
    backup = path.with_name(path.name + '.before-async-epaper-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.bak')
    if backup.exists():
        sys.exit('ERROR: Backup already exists. Try again in one second.')
    shutil.copy2(path, backup)
    temp = path.with_name('.' + path.name + '.async-epaper.tmp')
    if temp.exists():
        sys.exit(f'ERROR: Temporary file exists; original unchanged; backup at {backup}')
    try:
        temp.write_text(new, encoding='utf-8')
        shutil.copymode(path, temp)
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()
    print('PASS: async e-paper patch installed; Python syntax validated.')
    print('Backup:', backup)
    print('Restart muse_pi.py to use the new version. ESP32 does not need reflashing.')


if __name__ == '__main__':
    main()
