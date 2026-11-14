#!/usr/bin/env python3
"""Conservative Phase 3 Pi status extension for an existing Hey Muse muse_pi.py.

Adds an authenticated /api/v1/status endpoint and an OLED status indicator.
Does not alter /api/v1/reply or e-paper refresh logic.
Use --dry-run first. Backups are created before writing.
"""
import argparse
import ast
import difflib
import shutil
from pathlib import Path
from datetime import datetime

VALID = ('idle', 'listening', 'thinking', 'speaking', 'error')

def replace_once(src, old, new, label):
    n = src.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: expected exactly one anchor, found {n}; no changes made')
    return src.replace(old, new, 1)

def patch(src):
    if 'MUSE_LIVE_STATUS_PATCH_V1' in src:
        raise RuntimeError('Live-status patch already installed; no changes made')
    src = replace_once(src,
        '''        if self.path != "/api/v1/reply":
            self.respond(404, {"error": "not_found"})
            return''',
        '''        # MUSE_LIVE_STATUS_PATCH_V1: reply + authenticated live-status endpoints.
        if self.path not in ("/api/v1/reply", "/api/v1/status"):
            self.respond(404, {"error": "not_found"})
            return''', 'POST path check')
    src = replace_once(src,
        '''        value = obj.get("text")
''',
        '''        if self.path == "/api/v1/status":
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
''', 'payload validation')
    src = replace_once(src,
        '''        self.inbox = inbox
''',
        '''        self.inbox = inbox
        self.status_queue = queue.Queue(maxsize=32)
''', 'BridgeServer storage')
    src = replace_once(src,
        '''
    new_reply = False
''',
        '''
    new_reply = False
    live_status = "idle"
    live_status_at = time.monotonic()
    # Expire stale transient statuses if Wi-Fi drops or ESP32 reboots.
    LIVE_STATUS_TIMEOUT = 90.0
''', 'run_app state')
    src = replace_once(src,
        '''            status = ("NEW REPLY - KEY2" if new_reply else message)
            draw.text((4, 47), status[:20], fill="white")
''',
        '''            # Status line is independent of manual menu and e-paper view.
            if live_status != "idle":
                status = "MUSE: " + live_status.upper()
            else:
                status = ("NEW REPLY - KEY2" if new_reply else "MUSE: READY")
            draw.text((4, 47), status[:20], fill="white")
''', 'OLED status line')
    src = replace_once(src,
        '''        while True:
            received = inbox.collect()
''',
        '''        while True:
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
''', 'main loop')
    ast.parse(src)
    return src

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--file', type=Path, default=Path.home() / 'hey-muse-display' / 'muse_pi.py')
    args = ap.parse_args()
    original = args.file.read_text(encoding='utf-8')
    modified = patch(original)
    diff = ''.join(difflib.unified_diff(original.splitlines(True), modified.splitlines(True), fromfile='muse_pi.py (before)', tofile='muse_pi.py (proposed)'))
    if args.dry_run:
        print('PASS: all anchors unique, patched Python syntax valid. No files changed.\n')
        print(diff)
        return
    backup = args.file.with_name(args.file.name + '.before-live-status-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    shutil.copy2(args.file, backup)
    tmp = args.file.with_name(args.file.name + '.live-status.tmp')
    try:
        tmp.write_text(modified, encoding='utf-8')
        tmp.chmod(args.file.stat().st_mode & 0o777)
        tmp.replace(args.file)
    finally:
        if tmp.exists():
            tmp.unlink()
    print('PASS: live status receiver and OLED indicator installed.')
    print('Backup:', backup)
    print('New endpoint: POST /api/v1/status, Bearer token, JSON {"state":"listening"}')
    print('Existing reply endpoint and e-paper refresh code preserved.')
    print('Restart the running muse_pi.py process for changes to take effect.')

if __name__ == '__main__':
    main()
