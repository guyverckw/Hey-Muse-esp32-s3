#!/usr/bin/env python3
"""Phase 6 status tests: no GPIO, HTTP, e-paper, or hardware imports."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "muse_pi.py"
spec = importlib.util.spec_from_file_location("muse_pi_phase6", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class OledStatusTests(unittest.TestCase):
    def test_idle_is_static(self):
        self.assertEqual(mod.oled_animation_frame("idle", 0.0), ())
        self.assertEqual(mod.oled_animation_frame("error", 1.0), ())

    def test_active_states_animate(self):
        for name in ("listening", "thinking", "speaking"):
            self.assertNotEqual(mod.oled_animation_frame(name, 0.0),
                                mod.oled_animation_frame(name, 0.5))
            self.assertEqual(mod.oled_animation_frame(name, 0.0),
                             mod.oled_animation_frame(name, 1.5))

    def test_active_ai_status_overrides_epaper(self):
        self.assertEqual(mod.oled_footer("speaking", False, True, True, 150),
                         "MUSE: SPEAKING")

    def test_queue_countdown_and_busy(self):
        self.assertEqual(mod.oled_footer("idle", False, True, False, 42),
                         "EPAPER Q 42s")
        self.assertEqual(mod.oled_footer("idle", False, True, True, 0),
                         "EPAPER QUEUED")
        self.assertEqual(mod.oled_footer("idle", False, False, True, 0),
                         "EPAPER UPDATING")

    def test_latest_reply_and_ready(self):
        self.assertEqual(mod.oled_footer("idle", True, False, False, 0),
                         "NEW REPLY - KEY2")
        self.assertEqual(mod.oled_footer("idle", False, False, False, 0),
                         "MUSE: READY")


if __name__ == "__main__":
    unittest.main()
