import time
from collections.abc import Callable

from ns_controller.pb.ns_controller_pb2 import Button, ControllerState, Position, Stick


class EnhancedControllerState:
    def __init__(self, state: ControllerState | None = None):
        self.proto = state or ControllerState()
        self._notify: Callable[[], None] | None = None

    def set_notify(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked on every state mutation (press, release, stick, etc.).

        The Controller uses this to trigger an immediate HID report so the
        Switch sees state changes within ~1ms instead of waiting for the next
        periodic report (previously 30ms).
        """
        self._notify = callback

    def _changed(self) -> None:
        if self._notify is not None:
            self._notify()

    def click(self, *buttons: Button, duration: float = 0.1) -> ControllerState:
        self.press(*buttons)
        time.sleep(duration)
        self.release(*buttons)
        return self.proto

    def press(self, *buttons: Button) -> ControllerState:
        for button in buttons:
            self.proto.buttons |= (1 << button)
        self._changed()
        return self.proto

    def release(self, *buttons: Button) -> ControllerState:
        for button in buttons:
            self.proto.buttons &= ~(1 << button)
        self._changed()
        return self.proto

    def update_buttons(self, *buttons: Button, pressed: bool) -> ControllerState:
        if pressed:
            self.press(*buttons)
        else:
            self.release(*buttons)
        return self.proto

    def set_stick(self, stick: Stick, position: Position) -> ControllerState:
        match stick:
            case Stick.LS:
                self.proto.ls.CopyFrom(position)
            case Stick.RS:
                self.proto.rs.CopyFrom(position)
        self._changed()
        return self.proto

    def set_state(self, state: ControllerState) -> ControllerState:
        self.proto.CopyFrom(state)
        self._changed()
        return self.proto

    def clear(self) -> ControllerState:
        self.proto.Clear()
        self._changed()
        return self.proto
