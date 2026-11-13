"""Wire format shared with the firmware (firmware/src/link.h; spec: ns-automation docs/protocol.md).

wire: COBS( type:u8 | seq:u8 | payload | crc16:u16le ) | 0x00
"""

from __future__ import annotations

import struct
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

PROTO_VERSION = 1
MAX_FRAME = 256
MAX_PAYLOAD = MAX_FRAME - 4
KEYFRAMES_PER_LOAD = 15

# brain -> Pico
HELLO, PING, GET_STATUS, SET_STATE, MACRO_LOAD, MACRO_RUN, ABORT, REBOOT = (
    0x01,
    0x02,
    0x03,
    0x10,
    0x20,
    0x21,
    0x22,
    0x30,
)
# Pico -> brain
ACK, HELLO_REPLY, STATUS, MACRO_DONE, BOOT, STATUS_CHANGED, LOG = 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x8F

ACK_NAMES = {
    0: "OK",
    1: "BUSY",
    2: "BAD_ARG",
    3: "UNKNOWN_TYPE",
    4: "VERSION_MISMATCH",
    5: "MACRO_INCOMPLETE",
    6: "NOT_READY",
}
FLAG_NAMES = ["usb-mounted", "suspended", "handshake-done", "reports-flowing", "macro-running", "safety-release"]
RESULT_NAMES = {0: "completed", 1: "aborted", 2: "safety"}
RESET_NAMES = {0: "power-on", 1: "watchdog", 2: "reboot-command"}

# Button bits = Pro Controller input report layout (bytes 3..5), as in firmware procon.h.
BUTTONS = {
    "Y": 1 << 0,
    "X": 1 << 1,
    "B": 1 << 2,
    "A": 1 << 3,
    "R": 1 << 6,
    "ZR": 1 << 7,
    "MINUS": 1 << 8,
    "PLUS": 1 << 9,
    "RSTICK": 1 << 10,
    "LSTICK": 1 << 11,
    "HOME": 1 << 12,
    "CAPTURE": 1 << 13,
    "DOWN": 1 << 16,
    "UP": 1 << 17,
    "RIGHT": 1 << 18,
    "LEFT": 1 << 19,
    "L": 1 << 22,
    "ZL": 1 << 23,
}
CENTER = 2048


def button_bits(names: Iterable[str]) -> int:
    bits = 0
    for name in names:
        try:
            bits |= BUTTONS[name.upper()]
        except KeyError:
            raise ValueError(f"unknown button {name!r}; known: {', '.join(BUTTONS)}") from None
    return bits


def stick(value: float) -> int:
    """-1.0..1.0 -> 12-bit stick value (same rounding as the old Python controller)."""
    return max(0, min(4095, round((value + 1) * 2047.5)))


@dataclass(frozen=True)
class State:
    buttons: int = 0
    lx: int = CENTER
    ly: int = CENTER
    rx: int = CENTER
    ry: int = CENTER

    def pack(self) -> bytes:
        return struct.pack(
            "<IHHHH", self.buttons & 0xFFFFFF, *(v & 0xFFF for v in (self.lx, self.ly, self.rx, self.ry))
        )


NEUTRAL = State()


@dataclass(frozen=True)
class Keyframe:
    t_us: int  # from the start of the macro
    state: State

    def pack(self) -> bytes:
        return struct.pack("<I", self.t_us) + self.state.pack()


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def cobs_encode(data: bytes) -> bytes:
    out = bytearray([0])
    code_at, code = 0, 1
    for byte in data:
        if byte == 0:
            out[code_at] = code
            code_at, code = len(out), 1
            out.append(0)
        else:
            out.append(byte)
            code += 1
            if code == 0xFF:
                out[code_at] = code
                code_at, code = len(out), 1
                out.append(0)
    out[code_at] = code
    return bytes(out)


def cobs_decode(data: bytes) -> bytes | None:
    out = bytearray()
    i = 0
    while i < len(data):
        code = data[i]
        i += 1
        if code == 0 or i + code - 1 > len(data):
            return None
        out += data[i : i + code - 1]
        i += code - 1
        if code != 0xFF and i < len(data):
            out.append(0)
    return bytes(out)


def encode(type_: int, seq: int, payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload of {len(payload)} bytes exceeds {MAX_PAYLOAD}")
    raw = bytes([type_, seq]) + payload
    return cobs_encode(raw + struct.pack("<H", crc16(raw))) + b"\x00"


@dataclass(frozen=True)
class Frame:
    type: int
    seq: int
    payload: bytes


class Decoder:
    """Turns a byte stream into frames; bad frames are counted and dropped."""

    def __init__(self) -> None:
        self._buf = bytearray()
        self.bad = 0

    def feed(self, data: bytes) -> Iterator[Frame]:
        for byte in data:
            if byte != 0:
                if len(self._buf) < 2 * MAX_FRAME:
                    self._buf.append(byte)
                continue
            if not self._buf:
                continue  # back-to-back delimiters
            raw = cobs_decode(bytes(self._buf))
            self._buf.clear()
            if raw is None or len(raw) < 4 or crc16(raw[:-2]) != struct.unpack("<H", raw[-2:])[0]:
                self.bad += 1
                continue
            yield Frame(raw[0], raw[1], raw[2:-2])


def macro_load_payloads(macro_id: int, keyframes: list[Keyframe]) -> Iterator[bytes]:
    total = len(keyframes)
    for offset in range(0, total, KEYFRAMES_PER_LOAD):
        chunk = keyframes[offset : offset + KEYFRAMES_PER_LOAD]
        yield struct.pack("<HHHB", macro_id, total, offset, len(chunk)) + b"".join(k.pack() for k in chunk)
