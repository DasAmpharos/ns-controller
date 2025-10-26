"""
NXBT Macro Parser

Parses macro scripts that follow the NXBT syntax specification.
Each parsed macro returns a list of steps, where each step contains:
- state: ControllerState with buttons/sticks set
- duration: how long to hold this state (in seconds)
"""

import re
from typing import NamedTuple

from .controller import Buttons, ControllerState, StickPosition


class MacroStep(NamedTuple):
    """A single step in a macro sequence."""
    state: ControllerState
    duration: float  # seconds


# Map NXBT button names to our Buttons enum
BUTTON_MAPPING = {
    "Y": Buttons.Y,
    "X": Buttons.X,
    "B": Buttons.B,
    "A": Buttons.A,
    "R": Buttons.R,
    "ZR": Buttons.ZR,
    "MINUS": Buttons.MINUS,
    "PLUS": Buttons.PLUS,
    "R_STICK_PRESS": Buttons.RS,
    "L_STICK_PRESS": Buttons.LS,
    "HOME": Buttons.HOME,
    "CAPTURE": Buttons.CAPTURE,
    "DPAD_DOWN": Buttons.DPAD_DOWN,
    "DPAD_UP": Buttons.DPAD_UP,
    "DPAD_RIGHT": Buttons.DPAD_RIGHT,
    "DPAD_LEFT": Buttons.DPAD_LEFT,
    "L": Buttons.L,
    "ZL": Buttons.ZL,
}


def parse_macro(text: str) -> list[MacroStep]:
    """
    Parse a macro script and return a list of MacroSteps.

    The macro format follows NXBT spec:
    - Button inputs: "B 0.1s" or "A B 0.5s" (multiple buttons)
    - Wait: "0.1s" (no buttons)
    - Stick: "L_STICK@+000+100 0.5s"
    - Loops: "LOOP N" followed by indented block
    - Comments: lines starting with #
    """
    lines = _preprocess_lines(text)
    steps, _ = _parse_lines(lines, 0)
    return steps


def _preprocess_lines(text: str) -> list[str]:
    """Strip empty lines and comments, but preserve indentation."""
    lines = []
    for line in text.splitlines():
        # Strip trailing whitespace but keep leading whitespace
        line = line.rstrip()
        # Skip empty lines and comment-only lines
        if not line or line.lstrip().startswith("#"):
            continue
        lines.append(line)
    return lines


def _parse_lines(lines: list[str], start_idx: int, indent_level: int = 0) -> tuple[list[MacroStep], int]:
    """
    Parse lines starting at start_idx, respecting indentation levels.
    Returns (steps, next_index) where next_index is the first line not parsed.
    """
    steps = []
    idx = start_idx

    while idx < len(lines):
        line = lines[idx]

        # Calculate indentation level (4 spaces or 1 tab = 1 level)
        stripped = line.lstrip()
        current_indent = (len(line) - len(stripped)) // 4  # Assume 4 spaces per indent
        if line.startswith("\t"):
            current_indent = len(line) - len(line.lstrip("\t"))

        # If we've dedented, return to parent
        if current_indent < indent_level:
            return steps, idx

        # If over-indented, that's an error
        if current_indent > indent_level:
            raise ValueError(f"Unexpected indentation at line: {line}")

        # Handle LOOP
        if stripped.startswith("LOOP"):
            loop_match = re.match(r"LOOP\s+(\d+)", stripped)
            if not loop_match:
                raise ValueError(f"Invalid LOOP syntax: {line}")

            count = int(loop_match.group(1))
            # Parse the loop body (next indentation level)
            loop_steps, idx = _parse_lines(lines, idx + 1, indent_level + 1)

            # Expand the loop
            for _ in range(count):
                steps.extend(loop_steps)

            continue

        # Parse the actual command
        command_steps = _parse_command(stripped)
        steps.extend(command_steps)
        idx += 1

    return steps, idx


def _parse_command(line: str) -> list[MacroStep]:
    """
    Parse a single command line (non-LOOP, non-comment).

    Returns a list of MacroSteps. Most commands return 2 steps:
    1. The state with buttons pressed for the duration
    2. The state with buttons released (0 duration)

    Exception: Wait-only commands return 1 step with neutral state.
    """
    # Try to match stick input: L_STICK@+000+100 0.5s
    stick_match = re.match(r"^(L_STICK|R_STICK)@([+-]\d{3})([+-]\d{3})\s+(\d+(?:\.\d+)?)s$", line)
    if stick_match:
        stick_name, x_str, y_str, duration_str = stick_match.groups()
        x = int(x_str) / 100.0
        y = int(y_str) / 100.0
        duration = float(duration_str)

        # Create state with stick moved
        state_pressed = ControllerState()
        if stick_name == "L_STICK":
            state_pressed.ls = StickPosition(x=x, y=y)
        else:
            state_pressed.rs = StickPosition(x=x, y=y)

        # Return to neutral after
        state_released = ControllerState()

        return [
            MacroStep(state_pressed, duration),
            MacroStep(state_released, 0.0),
        ]

    # Try to match wait-only: 0.5s
    wait_match = re.match(r"^(\d+(?:\.\d+)?)s$", line)
    if wait_match:
        duration = float(wait_match.group(1))
        return [MacroStep(ControllerState(), duration)]

    # Try to match button input: B 0.1s or A B 0.5s
    button_match = re.match(r"^([A-Z_\s]+?)\s+(\d+(?:\.\d+)?)s$", line)
    if button_match:
        buttons_str, duration_str = button_match.groups()
        duration = float(duration_str)

        # Parse button names (space-separated)
        button_names = buttons_str.split()

        # Create state with buttons pressed
        state_pressed = ControllerState()
        for btn_name in button_names:
            if btn_name not in BUTTON_MAPPING:
                raise ValueError(f"Unknown button: {btn_name}")
            state_pressed.set_button(BUTTON_MAPPING[btn_name], True)

        # Create state with buttons released
        state_released = ControllerState()

        return [
            MacroStep(state_pressed, duration),
            MacroStep(state_released, 0.0),
        ]

    raise ValueError(f"Invalid macro command: {line}")
