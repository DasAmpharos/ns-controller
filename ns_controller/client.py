import time
from collections.abc import Generator

from ns_controller.pb.ns_controller_pb2 import (
    Button,
    ClickAction,
    ControllerState,
    HoldAction,
    Macro,
    MacroAction,
    MacroEvent,
    Position,
    RepeatClickAction,
    SetMarkAction,
    SetStickAction,
    SpamAction,
    Stick,
    WaitAction,
    WaitUntilAction,
)

from .client_transport import NsControllerTransport
from .state import EnhancedControllerState


class NsControllerClient:
    def __init__(self, transport: NsControllerTransport) -> None:
        self.state = EnhancedControllerState()
        self.transport = transport

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def press(self, *buttons: Button, send: bool = True, post_delay: float | None = 0.1) -> None:
        """
        Press buttons (adds to currently pressed buttons).
        Args:
            buttons: List of buttons to press
            send: If True, immediately send the state to the server
            post_delay: Optional delay in seconds after pressing the buttons
        """
        self.state.press(*buttons)
        if send:
            self.transport.send(self.state.proto)
        if post_delay:
            time.sleep(post_delay)

    def release(self, *buttons: Button, send: bool = True, post_delay: float | None = 0.1) -> None:
        """
        Release buttons (removes from currently pressed buttons).
        Args:
            buttons: List of buttons to release
            send: If True, immediately send the state to the server
            post_delay: Optional delay in seconds after releasing the buttons
        """
        self.state.release(*buttons)
        if send:
            self.transport.send(self.state.proto)
        if post_delay:
            time.sleep(post_delay)

    def click(self, *buttons: Button, down: float = 0.1, post_delay: float | None = 0.1) -> None:
        """
        Simulate a button click (press and release after a delay).
        Args:
            buttons: List of buttons to click
            down: Time in seconds to hold the buttons down
            post_delay: Optional delay in seconds after releasing the buttons
        """
        self.press(*buttons, send=True, post_delay=down)
        self.release(*buttons, send=True, post_delay=post_delay)

    def set_stick(self, stick: Stick, position: Position, send: bool = True, post_delay: float | None = 0.1) -> None:
        """
        Set a specific analog stick position (range -1.0 to 1.0).
        Args:
            stick: The stick to set (Stick.LS or Stick.RS)
            position: The position to set (x and y values; each from -1.0 to 1.0)
            send: If True, immediately send the state to the server
            post_delay: Optional delay in seconds after setting the stick
        """
        self.state.set_stick(stick, position)
        if send:
            self.transport.send(self.state.proto)
        if post_delay:
            time.sleep(post_delay)

    def set_state(self, controller_state: ControllerState, send: bool = True, post_delay: float | None = 0.1) -> None:
        """
        Directly set the controller state.
        Args:
            controller_state: The ControllerState to set
            send: If True, immediately send the state to the server
            post_delay: Optional delay in seconds after setting the state
        """
        self.state.set_state(controller_state)
        if send:
            self.transport.send(self.state.proto)
        if post_delay:
            time.sleep(post_delay)

    def clear(self, post_delay: float | None = 0.1):
        """
        Clear all inputs (buttons and sticks).
        Args:
            post_delay: Optional delay in seconds after clearing the state
        """
        self.state.clear()
        self.transport.send(self.state.proto)
        if post_delay:
            time.sleep(post_delay)

    def close(self):
        self.transport.close()

    def run_macro(self, macro: Macro) -> Generator[MacroEvent, None, None]:
        """Send a macro to the server and stream back progress events.

        Cancel by closing the generator. The server runs with monotonic clock
        timing and streams a MacroEvent per action.
        """
        yield from self.transport.run_macro(macro)


class MacroBuilder:
    """Fluent builder for constructing Macro protobuf messages.

    Example::

        macro = (MacroBuilder()
            .click(Button.A)
            .wait(20855)
            .mark("hold_start")
            .hold(Button.A, duration_ms=3000)
            .wait_until("hold_start", offset_ms=20645)
            .spam(Button.B, duration_ms=3000)
            .click(Button.A, count=3)
            .build())
    """

    def __init__(self):
        self._actions: list[MacroAction] = []

    def click(
        self,
        *buttons: Button,
        down_ms: int = 100,
        mark: str | None = None,
    ) -> "MacroBuilder":
        self._actions.append(
            MacroAction(
                click=ClickAction(
                    buttons=list(buttons),
                    down_ms=down_ms,
                    **({"mark": mark} if mark is not None else {}),
                )
            )
        )
        return self

    def repeat_click(
        self,
        *buttons: Button,
        count: int,
        down_ms: int = 100,
        gap_ms: int = 100,
        mark: str | None = None,
    ) -> "MacroBuilder":
        self._actions.append(
            MacroAction(
                repeat_click=RepeatClickAction(
                    buttons=list(buttons),
                    count=count,
                    down_ms=down_ms,
                    gap_ms=gap_ms,
                    **({"mark": mark} if mark is not None else {}),
                )
            )
        )
        return self

    def hold(self, *buttons: Button, duration_ms: int, mark: str | None = None) -> "MacroBuilder":
        self._actions.append(
            MacroAction(
                hold=HoldAction(
                    buttons=list(buttons),
                    duration_ms=duration_ms,
                    **({"mark": mark} if mark is not None else {}),
                )
            )
        )
        return self

    def wait(self, duration_ms: int) -> "MacroBuilder":
        self._actions.append(MacroAction(wait=WaitAction(duration_ms=duration_ms)))
        return self

    def spam(self, *buttons: Button, duration_ms: int, interval_ms: int = 100) -> "MacroBuilder":
        self._actions.append(
            MacroAction(
                spam=SpamAction(
                    buttons=list(buttons),
                    duration_ms=duration_ms,
                    interval_ms=interval_ms,
                )
            )
        )
        return self

    def mark(self, name: str) -> "MacroBuilder":
        self._actions.append(MacroAction(set_mark=SetMarkAction(name=name)))
        return self

    def wait_until(self, mark: str, offset_ms: int) -> "MacroBuilder":
        self._actions.append(
            MacroAction(
                wait_until=WaitUntilAction(
                    mark=mark,
                    offset_ms=offset_ms,
                )
            )
        )
        return self

    def set_stick(
        self,
        stick: Stick,
        x: float = 0.0,
        y: float = 0.0,
        duration_ms: int = 0,
    ) -> "MacroBuilder":
        self._actions.append(
            MacroAction(
                set_stick=SetStickAction(
                    stick=stick,
                    position=Position(x=x, y=y),
                    duration_ms=duration_ms,
                )
            )
        )
        return self

    def build(self) -> Macro:
        return Macro(actions=self._actions)
