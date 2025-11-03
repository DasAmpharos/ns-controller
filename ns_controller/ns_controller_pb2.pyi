from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Button(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BUTTON_UNSPECIFIED: _ClassVar[Button]
    A: _ClassVar[Button]
    B: _ClassVar[Button]
    X: _ClassVar[Button]
    Y: _ClassVar[Button]
    L: _ClassVar[Button]
    R: _ClassVar[Button]
    ZL: _ClassVar[Button]
    ZR: _ClassVar[Button]
    L_STICK: _ClassVar[Button]
    R_STICK: _ClassVar[Button]
    PLUS: _ClassVar[Button]
    MINUS: _ClassVar[Button]
    HOME: _ClassVar[Button]
    CAPTURE: _ClassVar[Button]
    DPAD_UP: _ClassVar[Button]
    DPAD_DOWN: _ClassVar[Button]
    DPAD_LEFT: _ClassVar[Button]
    DPAD_RIGHT: _ClassVar[Button]
    SL: _ClassVar[Button]
    SR: _ClassVar[Button]
BUTTON_UNSPECIFIED: Button
A: Button
B: Button
X: Button
Y: Button
L: Button
R: Button
ZL: Button
ZR: Button
L_STICK: Button
R_STICK: Button
PLUS: Button
MINUS: Button
HOME: Button
CAPTURE: Button
DPAD_UP: Button
DPAD_DOWN: Button
DPAD_LEFT: Button
DPAD_RIGHT: Button
SL: Button
SR: Button

class Buttons(_message.Message):
    __slots__ = ("mask", "pressed")
    MASK_FIELD_NUMBER: _ClassVar[int]
    PRESSED_FIELD_NUMBER: _ClassVar[int]
    mask: int
    pressed: _containers.RepeatedScalarFieldContainer[Button]
    def __init__(self, mask: _Optional[int] = ..., pressed: _Optional[_Iterable[_Union[Button, str]]] = ...) -> None: ...

class Stick(_message.Message):
    __slots__ = ("x", "y")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ...) -> None: ...

class ControllerState(_message.Message):
    __slots__ = ("buttons", "ls", "rs")
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    LS_FIELD_NUMBER: _ClassVar[int]
    RS_FIELD_NUMBER: _ClassVar[int]
    buttons: Buttons
    ls: Stick
    rs: Stick
    def __init__(self, buttons: _Optional[_Union[Buttons, _Mapping]] = ..., ls: _Optional[_Union[Stick, _Mapping]] = ..., rs: _Optional[_Union[Stick, _Mapping]] = ...) -> None: ...

class Ack(_message.Message):
    __slots__ = ("success", "previous_state")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    PREVIOUS_STATE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    previous_state: ControllerState
    def __init__(self, success: bool = ..., previous_state: _Optional[_Union[ControllerState, _Mapping]] = ...) -> None: ...
