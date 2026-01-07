from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Button(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
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

class Stick(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LS: _ClassVar[Stick]
    RS: _ClassVar[Stick]
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
LS: Stick
RS: Stick

class Position(_message.Message):
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
    buttons: int
    ls: Position
    rs: Position
    def __init__(self, buttons: _Optional[int] = ..., ls: _Optional[_Union[Position, _Mapping]] = ..., rs: _Optional[_Union[Position, _Mapping]] = ...) -> None: ...

class ClickRequest(_message.Message):
    __slots__ = ("buttons", "duration")
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    duration: float
    def __init__(self, buttons: _Optional[_Iterable[_Union[Button, str]]] = ..., duration: _Optional[float] = ...) -> None: ...

class PressRequest(_message.Message):
    __slots__ = ("buttons",)
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    def __init__(self, buttons: _Optional[_Iterable[_Union[Button, str]]] = ...) -> None: ...

class ReleaseRequest(_message.Message):
    __slots__ = ("buttons",)
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    def __init__(self, buttons: _Optional[_Iterable[_Union[Button, str]]] = ...) -> None: ...

class StickRequest(_message.Message):
    __slots__ = ("stick", "position")
    STICK_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    stick: Stick
    position: Position
    def __init__(self, stick: _Optional[_Union[Stick, str]] = ..., position: _Optional[_Union[Position, _Mapping]] = ...) -> None: ...
