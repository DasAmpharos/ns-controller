from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

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
    def __init__(self, x: float | None = ..., y: float | None = ...) -> None: ...

class ControllerState(_message.Message):
    __slots__ = ("buttons", "ls", "rs")
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    LS_FIELD_NUMBER: _ClassVar[int]
    RS_FIELD_NUMBER: _ClassVar[int]
    buttons: int
    ls: Position
    rs: Position
    def __init__(self, buttons: int | None = ..., ls: Position | _Mapping | None = ..., rs: Position | _Mapping | None = ...) -> None: ...

class ClickRequest(_message.Message):
    __slots__ = ("buttons", "duration")
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    duration: float
    def __init__(self, buttons: _Iterable[Button | str] | None = ..., duration: float | None = ...) -> None: ...

class PressRequest(_message.Message):
    __slots__ = ("buttons",)
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    def __init__(self, buttons: _Iterable[Button | str] | None = ...) -> None: ...

class ReleaseRequest(_message.Message):
    __slots__ = ("buttons",)
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    def __init__(self, buttons: _Iterable[Button | str] | None = ...) -> None: ...

class StickRequest(_message.Message):
    __slots__ = ("stick", "position")
    STICK_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    stick: Stick
    position: Position
    def __init__(self, stick: Stick | str | None = ..., position: Position | _Mapping | None = ...) -> None: ...

class ClickAction(_message.Message):
    __slots__ = ("buttons", "down_ms", "gap_ms", "mark")
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    DOWN_MS_FIELD_NUMBER: _ClassVar[int]
    GAP_MS_FIELD_NUMBER: _ClassVar[int]
    MARK_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    down_ms: int
    gap_ms: int
    mark: str
    def __init__(self, buttons: _Iterable[Button | str] | None = ..., down_ms: int | None = ..., gap_ms: int | None = ..., mark: str | None = ...) -> None: ...

class RepeatClickAction(_message.Message):
    __slots__ = ("buttons", "count", "down_ms", "gap_ms", "mark")
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    DOWN_MS_FIELD_NUMBER: _ClassVar[int]
    GAP_MS_FIELD_NUMBER: _ClassVar[int]
    MARK_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    count: int
    down_ms: int
    gap_ms: int
    mark: str
    def __init__(self, buttons: _Iterable[Button | str] | None = ..., count: int | None = ..., down_ms: int | None = ..., gap_ms: int | None = ..., mark: str | None = ...) -> None: ...

class HoldAction(_message.Message):
    __slots__ = ("buttons", "duration_ms", "mark")
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    MARK_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    duration_ms: int
    mark: str
    def __init__(self, buttons: _Iterable[Button | str] | None = ..., duration_ms: int | None = ..., mark: str | None = ...) -> None: ...

class WaitAction(_message.Message):
    __slots__ = ("duration_ms",)
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    duration_ms: int
    def __init__(self, duration_ms: int | None = ...) -> None: ...

class SpamAction(_message.Message):
    __slots__ = ("buttons", "duration_ms", "interval_ms")
    BUTTONS_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_MS_FIELD_NUMBER: _ClassVar[int]
    buttons: _containers.RepeatedScalarFieldContainer[Button]
    duration_ms: int
    interval_ms: int
    def __init__(self, buttons: _Iterable[Button | str] | None = ..., duration_ms: int | None = ..., interval_ms: int | None = ...) -> None: ...

class SetMarkAction(_message.Message):
    __slots__ = ("name",)
    NAME_FIELD_NUMBER: _ClassVar[int]
    name: str
    def __init__(self, name: str | None = ...) -> None: ...

class WaitUntilAction(_message.Message):
    __slots__ = ("mark", "offset_ms")
    MARK_FIELD_NUMBER: _ClassVar[int]
    OFFSET_MS_FIELD_NUMBER: _ClassVar[int]
    mark: str
    offset_ms: int
    def __init__(self, mark: str | None = ..., offset_ms: int | None = ...) -> None: ...

class SetStickAction(_message.Message):
    __slots__ = ("stick", "position", "duration_ms")
    STICK_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    stick: Stick
    position: Position
    duration_ms: int
    def __init__(self, stick: Stick | str | None = ..., position: Position | _Mapping | None = ..., duration_ms: int | None = ...) -> None: ...

class MacroAction(_message.Message):
    __slots__ = ("click", "hold", "wait", "spam", "set_mark", "wait_until", "set_stick", "repeat_click")
    CLICK_FIELD_NUMBER: _ClassVar[int]
    HOLD_FIELD_NUMBER: _ClassVar[int]
    WAIT_FIELD_NUMBER: _ClassVar[int]
    SPAM_FIELD_NUMBER: _ClassVar[int]
    SET_MARK_FIELD_NUMBER: _ClassVar[int]
    WAIT_UNTIL_FIELD_NUMBER: _ClassVar[int]
    SET_STICK_FIELD_NUMBER: _ClassVar[int]
    REPEAT_CLICK_FIELD_NUMBER: _ClassVar[int]
    click: ClickAction
    hold: HoldAction
    wait: WaitAction
    spam: SpamAction
    set_mark: SetMarkAction
    wait_until: WaitUntilAction
    set_stick: SetStickAction
    repeat_click: RepeatClickAction
    def __init__(self, click: ClickAction | _Mapping | None = ..., hold: HoldAction | _Mapping | None = ..., wait: WaitAction | _Mapping | None = ..., spam: SpamAction | _Mapping | None = ..., set_mark: SetMarkAction | _Mapping | None = ..., wait_until: WaitUntilAction | _Mapping | None = ..., set_stick: SetStickAction | _Mapping | None = ..., repeat_click: RepeatClickAction | _Mapping | None = ...) -> None: ...

class Macro(_message.Message):
    __slots__ = ("actions",)
    ACTIONS_FIELD_NUMBER: _ClassVar[int]
    actions: _containers.RepeatedCompositeFieldContainer[MacroAction]
    def __init__(self, actions: _Iterable[MacroAction | _Mapping] | None = ...) -> None: ...

class MacroEvent(_message.Message):
    __slots__ = ("action_index", "description", "completed", "error", "error_message")
    ACTION_INDEX_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    action_index: int
    description: str
    completed: bool
    error: bool
    error_message: str
    def __init__(self, action_index: int | None = ..., description: str | None = ..., completed: bool = ..., error: bool = ..., error_message: str | None = ...) -> None: ...
