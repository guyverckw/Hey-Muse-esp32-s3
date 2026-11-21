"""Modular Muse/Pi build guards: run from repository root with
python3 -m unittest esp32/tests/test_modular_pi_build.py

Source and config checks only. ESP-IDF builds of both profiles still required.
"""
from pathlib import Path
import re
import unittest

ESP = Path(__file__).resolve().parents[1]
ROOT = ESP.parent

def read(path):
    return (ESP / path).read_text(encoding="utf-8")


class ModularBuildTest(unittest.TestCase):
    def test_pi_option_off_by_default_and_requires_hatch(self):
        kconfig = read("components/muse/Kconfig")
        option = kconfig.split("config MUSE_PI_BRIDGE", 1)[1].split("config ", 1)[0]
        self.assertIn("depends on MUSE_HATCH", option)
        self.assertIn("default n", option)

    def test_bridge_compiled_only_when_enabled(self):
        cmake = read("components/muse/CMakeLists.txt")
        self.assertNotIn('"muse_chat_session.cpp" "muse_pi_bridge.cpp"', cmake)
        self.assertRegex(
            cmake,
            r'if\(CONFIG_MUSE_PI_BRIDGE\)[\s\S]*?list\(APPEND srcs "muse_pi_bridge.cpp"\)',
        )

    def test_standalone_noop_uses_compile_time_guard(self):
        header = read("components/muse/muse_pi_bridge.h")
        self.assertIn("#if CONFIG_MUSE_PI_BRIDGE", header)
        self.assertIn("static inline void muse_pi_bridge_enqueue(", header)
        self.assertIn("static inline void muse_pi_bridge_enqueue_status(", header)
        self.assertIn("(void)state;", header)

    def test_separate_build_directories_and_opt_in(self):
        board = read("tools/muse/board.sh")
        self.assertIn('case "${MUSE_PI_BRIDGE:-0}" in', board)
        self.assertIn('1) B=$B-pi;', board)
        self.assertIn("sdkconfig.muse-pi-bridge", board)
        self.assertIn('MUSE_PI_BRIDGE must be 0 or 1', board)
        self.assertIn('port=$(python', board)

    def test_pi_profile_and_private_token(self):
        overlay = read("devices/sdkconfig.muse-pi-bridge")
        self.assertIn("CONFIG_MUSE_PI_BRIDGE=y", overlay)
        self.assertNotIn("MUSE_PI_BRIDGE_TOKEN", overlay)
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/esp32/components/muse/muse_pi_bridge_config.h", ignore)
        config = read("components/muse/muse_pi_bridge_config.h.example")
        self.assertIn("REPLACE_WITH_PRIVATE", config)


if __name__ == "__main__":
    unittest.main()
