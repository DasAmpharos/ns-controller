"""Tests for tools/macro2c.py (nxbt macro -> keyframes). Run: python3 test/test_macro2c.py"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import macro2c  # noqa: E402

C = macro2c.CENTER
A, B, DOWN = macro2c.BUTTONS["A"], macro2c.BUTTONS["B"], macro2c.BUTTONS["DPAD_DOWN"]


def frames(text: str):
    return macro2c.to_keyframes(macro2c.parse(text.splitlines(), "t"), "t")


class MacroTests(unittest.TestCase):
    def test_lines_set_whole_state_and_end_neutral(self):
        self.assertEqual(frames("A B 0.1s\n0.5s\nA 100ms"), [
            (0, (A | B, C, C, C, C)), (100, (0, C, C, C, C)), (600, (A, C, C, C, C)), (700, (0, C, C, C, C))])

    def test_loop_with_indented_block(self):
        f = frames("LOOP 3\n    DPAD_DOWN 0.075s\n    0.075s\nA 0.1s")
        presses = [t for t, s in f if s[0] == DOWN]
        self.assertEqual(presses, [0, 150, 300])
        self.assertEqual(f[-2], (450, (A, C, C, C, C)))

    def test_sticks_map_to_12_bit_up_positive(self):
        f = frames("L_STICK@-100+100 0.5s\nR_STICK@+050+000 0.5s")
        self.assertEqual(f[0][1], (0, 0, 4095, C, C))
        self.assertEqual(f[1][1], (0, C, C, round(1.5 * 2047.5), C))
        self.assertEqual(f[-1], (1000, (0, C, C, C, C)))

    def test_comments_and_blank_lines(self):
        self.assertEqual(len(frames("# hi\n\nA 0.1s\n")), 2)

    def test_errors(self):
        for bad, msg in [("A 0.1", "duration"), ("Q 0.1s", "unknown input"), ("LOOP x\n    A 0.1s", "LOOP <count>"),
                         ("LOOP 2\nA 0.1s", "without an indented block"), ("A 0.1s\n    B 0.1s", "indentation"),
                         ("L_STICK@+101+000 0.1s", "outside")]:
            with self.subTest(bad=bad), self.assertRaisesRegex(macro2c.MacroError, msg):
                frames(bad)


if __name__ == "__main__":
    unittest.main()
