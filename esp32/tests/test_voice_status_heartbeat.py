"""Source-level regression checks for long-speech OLED status heartbeat.

Run from repository root:
  python3 -m unittest esp32/tests/test_voice_status_heartbeat.py
This is a guard on source structure, not a substitute for ESP-IDF build or
real ESP32 playback acceptance testing.
"""
from pathlib import Path
import re
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / "components/muse/muse_voice.c").read_text()


class VoiceStatusHeartbeatTest(unittest.TestCase):
    def test_heartbeat_interval_is_below_pi_expiry(self):
        interval = re.search(r"speaking_heartbeat_us\s*=\s*(\d+)\s*\*\s*1000000LL", SOURCE)
        self.assertIsNotNone(interval)
        self.assertLess(int(interval.group(1)), 90)
        self.assertGreaterEqual(int(interval.group(1)), 5)

    def test_heartbeat_only_while_playing(self):
        reply = SOURCE.split("static bool hatch_reply(bool *delivered)", 1)[1].split(
            "static void go_idle(const char *caption)\n{", 1
        )[0]
        self.assertRegex(
            reply,
            r'if \(speaking && esp_timer_get_time\(\) >= next_speaking_heartbeat_us\)\s*\{\s*'
            r'muse_pi_bridge_enqueue_status\("speaking"\);',
        )
        self.assertIn('muse_pi_bridge_enqueue_status("speaking");', reply)
        self.assertIn("next_speaking_heartbeat_us = esp_timer_get_time() + speaking_heartbeat_us;", reply)

    def test_idle_emitted_on_existing_idle_path(self):
        go_idle = SOURCE.split("static void go_idle(const char *caption)\n{", 1)[1]
        self.assertIn('muse_pi_bridge_enqueue_status("idle");', go_idle)


if __name__ == "__main__":
    unittest.main()
