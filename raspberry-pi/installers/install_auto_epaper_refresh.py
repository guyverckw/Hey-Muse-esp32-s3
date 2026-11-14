#!/usr/bin/env python3
"""Safely enable automatic refresh of the latest Hey Muse Pi reply.

Usage:
  python3 install_auto_epaper_refresh.py --dry-run
  python3 install_auto_epaper_refresh.py
"""
from pathlib import Path
import argparse
import ast
import datetime
import difflib
import shutil
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--file', type=Path, default=Path.home() / 'hey-muse-display' / 'muse_pi.py')
parser.add_argument('--dry-run', action='store_true')
args = parser.parse_args()
path = args.file.expanduser().resolve()
if not path.is_file():
    sys.exit(f'ERROR: File not found: {path}')
old = path.read_text(encoding='utf-8')
if 'AUTO_EPAPER_REFRESH_PATCH_V1' in old:
    sys.exit('Already installed; no changes made.')

changes = [
    (
        '    new_reply = False\n\n    def current():',
        '    new_reply = False\n    # AUTO_EPAPER_REFRESH_PATCH_V1: pending latest reply, handled in the main loop.\n'
        '    pending_auto_refresh = False\n\n    def current():',
        'initialise the pending flag'
    ),
    (
        '    def refresh():\n        nonlocal message, new_reply\n',
        '    def refresh():\n        nonlocal message, new_reply, pending_auto_refresh\n',
        'allow refresh to clear the pending flag'
    ),
    (
        '            message = "E-paper updated"\n            new_reply = False\n',
        '            message = "E-paper updated"\n            new_reply = False\n'
        '            if view == "reply" and history_index == -1:\n'
        '                pending_auto_refresh = False\n',
        'clear pending only when newest reply was displayed successfully'
    ),
    (
        '    print("New network replies are stored locally, NOT auto-refreshed on e-paper.")',
        '    print("New network replies auto-refresh when e-paper cooldown permits.")',
        'update information line'
    ),
    (
        '                new_reply = True\n'
        '                message = f"Received {received} reply"\n'
        '                print("Received", received, "reply(s), stored locally")\n'
        '                draw_oled()\n',
        '                new_reply = True\n'
        '                pending_auto_refresh = True\n'
        '                message = f"Received {received} reply"\n'
        '                print("Received", received, "reply(s), queued for automatic e-paper refresh")\n'
        '                draw_oled()\n',
        'queue newly received replies'
    ),
    (
        '            if time.monotonic() - last_redraw > 1.0:\n',
        '            # Refresh on the main thread only, respecting the existing 180s cooldown.\n'
        '            # Multiple incoming replies collapse into the newest saved message.\n'
        '            if pending_auto_refresh and inbox.messages and inbox.remaining() == 0:\n'
        '                view, history_index, page = "reply", -1, 0\n'
        '                print("Auto-refresh: showing the latest AI reply")\n'
        '                try:\n'
        '                    refresh()\n'
        '                except Exception as exc:\n'
        '                    # refresh() persists its cooldown before accessing e-paper.\n'
        '                    # Keep pending to retry after the cooldown; do not kill the UI.\n'
        '                    print(f"Automatic e-paper refresh failed: {exc!r}", flush=True)\n'
        '            if time.monotonic() - last_redraw > 1.0:\n',
        'schedule automatic refresh in main loop'
    ),
]
new = old
for before, after, desc in changes:
    count = new.count(before)
    if count != 1:
        sys.exit(f'ERROR: Expected exactly one match to {desc!r}, found {count}. No changes made.')
    new = new.replace(before, after, 1)
try:
    ast.parse(new, filename=str(path))
except SyntaxError as exc:
    sys.exit(f'ERROR: Patched file would have invalid Python syntax: {exc}. No changes made.')

if args.dry_run:
    print('PASS: All six patch anchors found. Patched Python syntax valid. No files changed.')
    for line in difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile='muse_pi.py (existing)', tofile='muse_pi.py (proposed)', lineterm=''):
        print(line)
    sys.exit(0)

stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup = path.with_name(f'{path.name}.before-auto-refresh-{stamp}.bak')
if backup.exists():
    sys.exit(f'ERROR: Backup already exists: {backup}. No changes made.')
shutil.copy2(path, backup)
temp = path.with_name(f'.{path.name}.auto-refresh.tmp')
if temp.exists():
    sys.exit(f'ERROR: Temporary file exists: {temp}; backup created at {backup}, original unchanged.')
try:
    temp.write_text(new, encoding='utf-8')
    shutil.copymode(path, temp)
    temp.replace(path)
except Exception:
    if temp.exists():
        temp.unlink()
    raise
print(f'PASS: Installed automatic e-paper refresh in {path}')
print(f'Backup: {backup}')
print('Python syntax validated. Restart your Pi application/service to activate the change.')
