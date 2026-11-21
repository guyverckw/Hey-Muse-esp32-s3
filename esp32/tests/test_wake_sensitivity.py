"""Source regression checks for Phase 7 wake sensitivity policy.

Run: python3 -m unittest esp32/tests/test_wake_sensitivity.py
The true first-try detection and false activation rates require physical tests.
"""
from pathlib import Path
import re
import unittest

WAKE_CPP = Path(__file__).resolve().parents[1] / "components/muse/muse_wake.cpp"
VOICE_C = Path(__file__).resolve().parents[1] / "components/muse/muse_voice.c"


class WakeSensitivityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wake = WAKE_CPP.read_text(encoding="utf-8")
        cls.voice = VOICE_C.read_text(encoding="utf-8")

    def test_threshold_is_90_percent(self):
        self.assertRegex(self.wake, r"PROBABILITY_CUTOFF\s*=\s*static_cast<uint8_t>\(0\.90f \* 255\.0f\)")
        self.assertNotIn("0.99f * 255.0f", self.wake)

    def test_six_results_still_averaged(self):
        self.assertRegex(self.wake, r"PROBABILITY_WINDOW\s*=\s*6;")
        self.assertIn("if (s_probability_fill < PROBABILITY_WINDOW)", self.wake)
        self.assertIn("return sum > static_cast<uint32_t>(PROBABILITY_CUTOFF) * PROBABILITY_WINDOW;", self.wake)

    def test_wake_detector_and_mic_still_in_existing_voice_path(self):
        self.assertIn("muse_wake_process(s_chunk, MUSE_AUDIO_CHUNK)", self.voice)
        self.assertIn("muse_settings_mic_gain()", self.voice)
        self.assertIn("muse_wake_reset();", self.voice)


if __name__ == "__main__":
    unittest.main()
