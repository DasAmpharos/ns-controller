#!/usr/bin/env python3
"""Compile nxbt-format macro files into a C keyframe table for the firmware's player.

    python3 tools/macro2c.py out.h sequences/1-input-test.txt sequences/2-nxbt-demo.txt

nxbt macro format (https://github.com/Brikwerk/nxbt): every line sets the *whole* controller state for a duration,
then the next line replaces it.

    A B 0.1s                 hold A and B for 100 ms
    0.5s                     nothing pressed for 500 ms
    L_STICK@-100+050 0.75s   left stick at x=-100%, y=+50% (up is +) for 750 ms
    LOOP 12                  repeat the indented block 12 times
        DPAD_DOWN 0.075s
        0.075s
    # comment

The sequence number (BOOTSEL press count) comes from the file order; names come from the file names.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# nxbt input name -> PROCON_BTN_* bit (see src/procon.h)
BUTTONS = {
    "Y": 1 << 0, "X": 1 << 1, "B": 1 << 2, "A": 1 << 3, "JCR_SR": 1 << 4, "JCR_SL": 1 << 5, "R": 1 << 6, "ZR": 1 << 7,
    "MINUS": 1 << 8, "PLUS": 1 << 9, "R_STICK_PRESS": 1 << 10, "L_STICK_PRESS": 1 << 11, "HOME": 1 << 12,
    "CAPTURE": 1 << 13, "DPAD_DOWN": 1 << 16, "DPAD_UP": 1 << 17, "DPAD_RIGHT": 1 << 18, "DPAD_LEFT": 1 << 19,
    "JCL_SR": 1 << 20, "JCL_SL": 1 << 21, "L": 1 << 22, "ZL": 1 << 23,
}
CENTER = 0x800
STICK_RE = re.compile(r"^([LR])_STICK@([+-]\d{3})([+-]\d{3})$")
DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)(ms|s)$")
MIN_EDGE_MS = 24  # same rule as the brain's MacroBuilder: shorter presses/releases may be missed


class MacroError(ValueError):
    pass


def axis(percent: int) -> int:
    """-100..100 % -> 12-bit stick value, same rounding as the old Python controller."""
    if not -100 <= percent <= 100:
        raise MacroError(f"stick value {percent} outside -100..100")
    return round((1 + percent / 100) * 2047.5)


def parse_duration(token: str, where: str) -> int:
    m = DURATION_RE.match(token)
    if not m:
        raise MacroError(f"{where}: expected a duration like 0.1s or 100ms, got {token!r}")
    value = float(m.group(1))
    return round(value * 1000) if m.group(2) == "s" else round(value)


def parse(lines: list[str], name: str) -> list[tuple[tuple[int, int, int, int, int], int]]:
    """Return [(state, duration_ms)], state = (buttons, lx, ly, rx, ry)."""
    steps: list[tuple[tuple[int, int, int, int, int], int]] = []
    i = 0
    rows = [(n + 1, line.rstrip()) for n, line in enumerate(lines)]
    rows = [(n, line) for n, line in rows if line.strip() and not line.strip().startswith("#")]

    def indent(line: str) -> int:
        return len(line) - len(line.lstrip())

    def block(start: int, level: int) -> tuple[list, int]:
        out = []
        j = start
        while j < len(rows) and indent(rows[j][1]) >= level:
            n, line = rows[j]
            if indent(line) > level:
                raise MacroError(f"{name}:{n}: unexpected indentation")
            tokens = line.split()
            if tokens[0] == "LOOP":
                if len(tokens) != 2 or not tokens[1].isdigit():
                    raise MacroError(f"{name}:{n}: expected 'LOOP <count>'")
                if j + 1 >= len(rows) or indent(rows[j + 1][1]) <= level:
                    raise MacroError(f"{name}:{n}: LOOP without an indented block")
                body, j = block(j + 1, indent(rows[j + 1][1]))
                out += body * int(tokens[1])
                continue
            *inputs, duration = tokens
            ms = parse_duration(duration, f"{name}:{n}")
            buttons, lx, ly, rx, ry = 0, CENTER, CENTER, CENTER, CENTER
            for token in inputs:
                if token in BUTTONS:
                    buttons |= BUTTONS[token]
                elif m := STICK_RE.match(token):
                    x, y = axis(int(m.group(2))), axis(int(m.group(3)))
                    if m.group(1) == "L":
                        lx, ly = x, y
                    else:
                        rx, ry = x, y
                else:
                    raise MacroError(f"{name}:{n}: unknown input {token!r}")
            out.append(((buttons, lx, ly, rx, ry), ms))
            j += 1
        return out, j

    steps, i = block(0, 0)
    if i != len(rows):
        raise MacroError(f"{name}:{rows[i][0]}: unexpected indentation")
    return steps


def to_keyframes(steps, name: str) -> list[tuple[int, tuple[int, int, int, int, int]]]:
    """Absolute keyframes (t_ms, state), merged where nothing changes, ending neutral."""
    neutral = (0, CENTER, CENTER, CENTER, CENTER)
    frames: list[tuple[int, tuple]] = [(0, neutral)]
    t = 0
    released_at: dict[int, int] = {}
    for state, ms in steps:
        prev = frames[-1][1]
        if state != prev:
            pressed = state[0] & ~prev[0]
            for bit in range(24):
                if pressed >> bit & 1 and bit in released_at and t - released_at[bit] < MIN_EDGE_MS:
                    print(f"warning: {name}: button bit {bit} re-pressed {t - released_at[bit]} ms after release "
                          f"at {t} ms; the game may see one long press", file=sys.stderr)
            for bit in range(24):
                if prev[0] >> bit & 1 and not state[0] >> bit & 1:
                    released_at[bit] = t
            if frames[-1][0] == t:
                frames[-1] = (t, state)
            else:
                frames.append((t, state))
        t += ms
    if frames[-1][1] != neutral:
        frames.append((t, neutral))
    elif frames[-1][0] != t:
        frames.append((t, neutral))  # keep the trailing pause so "done" is reported after it
    return frames


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    out = Path(argv[1])
    parts = ["// Generated by tools/macro2c.py from sequences/*.txt; do not edit.", "#pragma once", "",
             '#include "player.h"', ""]
    table = []
    for path in map(Path, argv[2:]):
        name = re.sub(r"^\d+-", "", path.stem)
        frames = to_keyframes(parse(path.read_text().splitlines(), path.name), name)
        ident = "SEQ_" + re.sub(r"\W", "_", name).upper()
        parts.append(f"// {path.name}: {len(frames)} keyframes, {frames[-1][0] / 1000:.2f} s")
        parts.append(f"static const keyframe_t {ident}[] = {{")
        for t, (b, lx, ly, rx, ry) in frames:
            parts.append(f"    {{{t}, 0x{b:06x}, {lx}, {ly}, {rx}, {ry}}},")
        parts.append("};")
        parts.append("")
        table.append(f'    {{"{name}", {ident}, {len(frames)}}},')
        print(f"{path.name}: {name}, {len(frames)} keyframes, {frames[-1][0] / 1000:.2f} s", file=sys.stderr)
    parts.append("static const sequence_t SEQUENCES[] = {")
    parts += table
    parts.append("};")
    parts.append(f"#define SEQUENCE_COUNT {len(table)}")
    out.write_text("\n".join(parts) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except MacroError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
