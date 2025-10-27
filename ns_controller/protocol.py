import struct
from dataclasses import dataclass, field
from enum import IntEnum


class MessageType(IntEnum):
    PING = 0
    INPUT = 1


class Button(IntEnum):
    A = 0
    B = 1
    X = 2
    Y = 3
    L = 4
    R = 5
    ZL = 6
    ZR = 7
    PLUS = 8
    MINUS = 9
    CAPTURE = 10
    HOME = 11


@dataclass
class Buttons:
    a: bool = False
    b: bool = False
    x: bool = False
    y: bool = False
    l: bool = False
    r: bool = False
    zl: bool = False
    zr: bool = False
    plus: bool = False
    minus: bool = False
    capture: bool = False
    home: bool = False


@dataclass
class Stick:
    x: float = 0.0
    y: float = 0.0
    pressed: bool = False


@dataclass
class Sticks:
    left: Stick = field(default_factory=Stick)
    right: Stick = field(default_factory=Stick)


@dataclass
class Dpad:
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False


@dataclass
class ControllerInput:
    buttons: Buttons = field(default_factory=Buttons)
    sticks: Sticks = field(default_factory=Sticks)
    dpad: Dpad = field(default_factory=Dpad)


InputRequestStruct = struct.Struct("12B2d1B2d1B4B2d")


@dataclass
class InputRequest:
    controller_input: ControllerInput
    down: float
    up: float

    @classmethod
    def unpack(cls, data: bytes) -> "InputRequest":
        unpacked = InputRequestStruct.unpack(data)
        return cls(
            controller_input=ControllerInput(
                buttons=Buttons(
                    a=bool(unpacked[0]),
                    b=bool(unpacked[1]),
                    x=bool(unpacked[2]),
                    y=bool(unpacked[3]),
                    l=bool(unpacked[4]),
                    r=bool(unpacked[5]),
                    zl=bool(unpacked[6]),
                    zr=bool(unpacked[7]),
                    plus=bool(unpacked[8]),
                    minus=bool(unpacked[9]),
                    capture=bool(unpacked[10]),
                    home=bool(unpacked[11]),
                ),
                sticks=Sticks(
                    left=Stick(
                        x=unpacked[12],
                        y=unpacked[13],
                        pressed=bool(unpacked[14])
                    ),
                    right=Stick(
                        x=unpacked[15],
                        y=unpacked[16],
                        pressed=bool(unpacked[17])
                    ),
                ),
                dpad=Dpad(
                    up=bool(unpacked[18]),
                    down=bool(unpacked[19]),
                    left=bool(unpacked[20]),
                    right=bool(unpacked[21])
                )
            ),
            down=unpacked[22],
            up=unpacked[23]
        )
