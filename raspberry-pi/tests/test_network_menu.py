#!/usr/bin/env python3
"""Phase 6b link/ESP32 indicator & menu tests; does not access GPIO or network."""
import ast
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

source = Path(__file__).resolve().parents[1] / "muse_pi.py"
spec = importlib.util.spec_from_file_location("muse_pi_phase6b", source)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class NetworkIndicatorTests(unittest.TestCase):
    def test_wifi_link_only(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "wlan0").mkdir()
            (root / "wlan0" / "operstate").write_text("up\n")
            self.assertEqual(mod.pi_link_state(root), "W")
            # An active kernel link is not evidence of internet reachability.
            self.assertFalse(mod.esp32_seen_recently(None, 100.0))

    def test_eth_link_fallback_and_missing(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(mod.pi_link_state(root), "-")
            (root / "wlan0").mkdir()
            (root / "wlan0" / "operstate").write_text("down\n")
            (root / "eth0").mkdir()
            (root / "eth0" / "operstate").write_text("up\n")
            self.assertEqual(mod.pi_link_state(root), "E")
            (root / "wlan0" / "operstate").write_text("up\n")
            self.assertEqual(mod.pi_link_state(root), "W")

    def test_esp32_recent_status_expires(self):
        self.assertFalse(mod.esp32_seen_recently(None, 100))
        self.assertTrue(mod.esp32_seen_recently(20, 109))
        self.assertFalse(mod.esp32_seen_recently(20, 110))
        self.assertFalse(mod.esp32_seen_recently(150, 100))

    def test_network_clock_initialised_before_first_poll(self):
        """Regression: the first UI iteration must not reference stale 'now'."""
        tree = ast.parse(source.read_text(encoding="utf-8"))
        run = next(node for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name == "run_app")
        loop = next(node for node in ast.walk(run) if isinstance(node, ast.While))
        time_assign = []
        network_if = []
        for stmt in loop.body:
            if isinstance(stmt, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "now" for t in stmt.targets):
                time_assign.append(stmt.lineno)
            if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Compare):
                if isinstance(stmt.test.left, ast.Name) and stmt.test.left.id == "now":
                    network_if.append(stmt.lineno)
        self.assertTrue(time_assign, "UI main loop must initialise now")
        self.assertTrue(network_if, "UI main loop must contain the network poll")
        self.assertLess(time_assign[0], network_if[0],
                        "time.monotonic() must run before first network poll")

    def test_menu_position_and_bounds(self):
        self.assertEqual(mod.menu_line(0, ["Latest reply", "Older reply"]),
                         "> Latest reply  1/2")
        self.assertIn("2/2", mod.menu_line(1, ["Latest reply", "Older reply"]))
        self.assertLessEqual(len(mod.menu_line(0, ["Latest reply", "Older reply"])), 20)


if __name__ == "__main__":
    unittest.main()
