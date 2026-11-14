#!/usr/bin/env python3
"""GPIO-free checks for compact Unicode pagination and cooldown configuration."""
import importlib.util
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("muse_pi", ROOT / "muse_pi.py")
muse_pi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(muse_pi)


class EpaperPaginationTests(unittest.TestCase):
    def test_compact_layout_paginates_long_english_reply(self):
        text = " ".join(["English text should wrap across a compact page."] * 150)
        pages = muse_pi.paginate(text, heading="AI RESPONSE")
        self.assertGreater(len(pages), 1)
        self.assertLessEqual(max(map(len, pages)), 17)
        self.assertTrue(all(p for p in pages))

    def test_cjk_layout_keeps_unicode_text(self):
        text = ("繁體中文：香港。简体中文：人工智能。日本語：こんにちは。" * 90)
        pages = muse_pi.paginate(text, heading="AI RESPONSE")
        self.assertGreater(len(pages), 1)
        self.assertEqual("".join("".join(p) for p in pages).replace(" ", ""), text.replace(" ", ""))

    def test_page_numbers_match_rendered_count(self):
        text = "A longer response. " * 250
        pages = muse_pi.paginate(text, heading="AI RESPONSE")
        black, yellow, total = muse_pi.build_image(text, "AI RESPONSE", 1)
        self.assertEqual(total, len(pages))
        self.assertEqual(black.size, (muse_pi.EPD_W, muse_pi.EPD_H))
        self.assertEqual(yellow.size, black.size)


if __name__ == "__main__":
    unittest.main()
