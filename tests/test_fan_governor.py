from __future__ import annotations

import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOVERNOR_PATH = ROOT / "ansible/roles/fan/files/strix-fan-governor"
LOADER = importlib.machinery.SourceFileLoader("strix_fan_governor", str(GOVERNOR_PATH))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
assert SPEC is not None
GOVERNOR = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(GOVERNOR)


class FanGovernorTest(unittest.TestCase):
    def test_busy_immediately_selects_max_and_resets_hold(self) -> None:
        state, last_busy = GOVERNOR.next_state("auto", 10.0, 20.0, 5, 5, 300)
        self.assertEqual(state, "max")
        self.assertEqual(last_busy, 20.0)

    def test_idle_waits_for_full_hold(self) -> None:
        before, _ = GOVERNOR.next_state("max", 10.0, 309.9, 0, 5, 300)
        after, _ = GOVERNOR.next_state("max", 10.0, 310.0, 0, 5, 300)
        self.assertEqual(before, "max")
        self.assertEqual(after, "auto")

    def test_gpu_busy_reader_uses_max_valid_counter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first"
            second = root / "second"
            invalid = root / "invalid"
            first.write_text("0\n", encoding="ascii")
            second.write_text("87\n", encoding="ascii")
            invalid.write_text("unknown\n", encoding="ascii")
            self.assertEqual(GOVERNOR.read_gpu_busy([first, second, invalid]), 87)

    def test_gpu_busy_reader_fails_closed_without_valid_counter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid"
            path.write_text("101\n", encoding="ascii")
            with self.assertRaisesRegex(RuntimeError, "no valid GPU busy counter"):
                GOVERNOR.read_gpu_busy([path])

    def test_direct_fan_writes_match_controller_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for number in range(1, 4):
                fan = root / f"fan{number}"
                fan.mkdir()
                (fan / "mode").write_text("auto\n", encoding="ascii")
                (fan / "level").write_text("1\n", encoding="ascii")

            GOVERNOR.write_fans(root, "max")
            for number in range(1, 4):
                fan = root / f"fan{number}"
                self.assertEqual((fan / "mode").read_text(), "fixed\n")
                self.assertEqual((fan / "level").read_text(), "5\n")

            GOVERNOR.write_fans(root, "auto")
            for number in range(1, 4):
                self.assertEqual((root / f"fan{number}" / "mode").read_text(), "auto\n")


if __name__ == "__main__":
    unittest.main()
