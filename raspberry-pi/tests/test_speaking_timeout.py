"""Regression checks for Pi-only long SPEAKING state timeout policy."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "muse_pi.py"


def load_policy():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_app")
    bindings = {}
    for n in ast.walk(run):
        if isinstance(n, ast.Assign):
            for target in n.targets:
                if isinstance(target, ast.Name) and target.id in (
                    "LIVE_STATUS_TIMEOUT", "SPEAKING_STATUS_TIMEOUT"
                ):
                    bindings[target.id] = ast.literal_eval(n.value) if isinstance(n.value, ast.Constant) else eval(
                        compile(ast.Expression(n.value), "<test>", "eval"), {"__builtins__": {}}, {}
                    )
    return bindings, run


class StatusTimeoutTest(unittest.TestCase):
    def test_speaking_timeout_exceeds_long_voice_turn(self):
        bindings, _ = load_policy()
        self.assertEqual(bindings["LIVE_STATUS_TIMEOUT"], 90)
        self.assertGreaterEqual(bindings["SPEAKING_STATUS_TIMEOUT"], 12 * 60)

    def test_speaking_timeout_is_finite(self):
        bindings, _ = load_policy()
        self.assertLessEqual(bindings["SPEAKING_STATUS_TIMEOUT"], 30 * 60)

    def test_idle_event_has_priority_over_timeout(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        run = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run_app")
        source = ast.get_source_segment(SOURCE.read_text(encoding="utf-8"), run)
        self.assertIn('live_status = newest_status', source)
        self.assertIn('elif live_status != "idle":', source)
        self.assertIn('SPEAKING_STATUS_TIMEOUT if live_status == "speaking"', source)
        self.assertLess(source.index('live_status = newest_status'), source.index('elif live_status != "idle":'))


if __name__ == "__main__":
    unittest.main()
