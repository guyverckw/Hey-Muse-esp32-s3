#!/usr/bin/env python3
"""No GPIO, network, or token tests for the Phase 5 one-process lock."""
import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("muse_pi", ROOT / "muse_pi.py")
muse_pi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(muse_pi)


class SingletonTests(unittest.TestCase):
    def test_second_instance_blocked_and_crash_safe_lock_released(self):
        with TemporaryDirectory() as tmp:
            with patch.object(muse_pi, "config_dir", return_value=Path(tmp)):
                fd = muse_pi.acquire_instance_lock()
                try:
                    with self.assertRaises(SystemExit):
                        muse_pi.acquire_instance_lock()
                finally:
                    os.close(fd)
                fd = muse_pi.acquire_instance_lock()
                os.close(fd)

    def test_lock_file_permissions_private(self):
        with TemporaryDirectory() as tmp:
            with patch.object(muse_pi, "config_dir", return_value=Path(tmp)):
                fd = muse_pi.acquire_instance_lock()
                try:
                    mode = (Path(tmp) / "muse_pi.lock").stat().st_mode & 0o777
                    self.assertEqual(mode & 0o077, 0)
                finally:
                    os.close(fd)


if __name__ == "__main__":
    unittest.main()
