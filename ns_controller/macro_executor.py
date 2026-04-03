import threading
import time
from typing import Final

from loguru import logger

from ns_controller.pb.ns_controller_pb2 import (
    Macro,
    MacroAction,
    Position,
    Stick,
)
from ns_controller.state import EnhancedControllerState


class MacroExecutor:
    """Executes a Macro server-side with monotonic clock timing.

    All waits use time.monotonic() for drift-free scheduling. Named marks
    allow WaitUntil actions to reference absolute points in the macro timeline.

    Writes directly to the shared EnhancedControllerState — coexists safely
    with the gRPC RPCs and GamepadInput (last write wins).
    """

    def __init__(self, macro: Macro, state: EnhancedControllerState, cancel: threading.Event):
        self.macro: Final = macro
        self.state: Final = state
        self.cancel: Final = cancel
        self.marks: dict[str, float] = {}

    def execute(self) -> None:
        for action in self.macro.actions:
            if self.cancel.is_set():
                return
            try:
                self._execute_action(action)
            except Exception as e:
                logger.exception(f"Macro action failed: {e}")
                return

    def _execute_action(self, action: MacroAction) -> None:
        match action.WhichOneof("action"):
            case "click":
                self._do_click(action.click)
            case "repeat_click":
                self._do_repeat_click(action.repeat_click)
            case "hold":
                self._do_hold(action.hold)
            case "wait":
                self._do_wait(action.wait)
            case "spam":
                self._do_spam(action.spam)
            case "set_mark":
                self._do_set_mark(action.set_mark)
            case "wait_until":
                self._do_wait_until(action.wait_until)
            case "set_stick":
                self._do_set_stick(action.set_stick)
            case which:
                raise ValueError(f"Unknown action type: {which}")

    # -- Action implementations --------------------------------------------------

    def _do_click(self, action) -> None:
        down_s = (action.down_ms or 100) / 1000.0
        start = time.monotonic()
        if action.HasField("mark"):
            self.marks[action.mark] = start
        self.state.press(*action.buttons)
        self._sleep_until(start + down_s)
        self.state.release(*action.buttons)

    def _do_repeat_click(self, action) -> None:
        count = max(action.count, 1)
        down_s = (action.down_ms or 100) / 1000.0
        gap_s = (action.gap_ms or 100) / 1000.0
        cycle_s = down_s + gap_s

        start = time.monotonic()
        if action.HasField("mark"):
            self.marks[action.mark] = start
        for i in range(count):
            if self.cancel.is_set():
                return
            self.state.press(*action.buttons)
            self._sleep_until(start + i * cycle_s + down_s)
            self.state.release(*action.buttons)
            if i < count - 1:
                self._sleep_until(start + i * cycle_s + cycle_s)

    def _do_hold(self, action) -> None:
        press_time = time.monotonic()
        if action.HasField("mark"):
            self.marks[action.mark] = press_time
        self.state.press(*action.buttons)
        self._sleep_until(press_time + action.duration_ms / 1000.0)
        self.state.release(*action.buttons)

    def _do_wait(self, action) -> None:
        self._sleep(action.duration_ms / 1000.0)

    def _do_spam(self, action) -> None:
        interval_s = (action.interval_ms or 100) / 1000.0
        down_s = interval_s * 0.4
        up_s = interval_s * 0.6
        end_time = time.monotonic() + (action.duration_ms / 1000.0)

        while time.monotonic() < end_time:
            if self.cancel.is_set():
                self.state.release(*action.buttons)
                return
            self.state.press(*action.buttons)
            self._sleep(down_s)
            self.state.release(*action.buttons)
            self._sleep(up_s)

    def _do_set_mark(self, action) -> None:
        self.marks[action.name] = time.monotonic()

    def _do_wait_until(self, action) -> None:
        mark_time = self.marks.get(action.mark)
        if mark_time is None:
            raise ValueError(f"Unknown mark: '{action.mark}'")
        self._sleep_until(mark_time + (action.offset_ms / 1000.0))

    def _do_set_stick(self, action) -> None:
        self.state.set_stick(action.stick, action.position)
        if action.duration_ms > 0:
            self._sleep(action.duration_ms / 1000.0)
            self.state.set_stick(action.stick, Position(x=0.0, y=0.0))

    # -- Timing helpers ----------------------------------------------------------

    # Mirrors EonTimer's timer worker constants:
    # SPINWAIT_MS threshold below which we switch to a tight spin-wait loop.
    _SPINWAIT_S: Final = 0.002
    # Default refreshInterval — max duration of a single coarse sleep iteration.
    _REFRESH_S: Final = 0.008

    def _sleep(self, duration_s: float) -> None:
        self._sleep_until(time.monotonic() + duration_s)

    def _sleep_until(self, target: float) -> None:
        """Sleep until an absolute monotonic time with sub-ms precision.

        Mirrors EonTimer's timer worker approach:
        - Coarse sleep of min(remaining - _SPINWAIT_S, _REFRESH_S) while
          further than _SPINWAIT_S from the target.
        - Tight spin-wait for the final _SPINWAIT_S window.
        """
        while not self.cancel.is_set():
            remaining = target - time.monotonic()
            if remaining <= 0:
                return
            if remaining > self._SPINWAIT_S:
                time.sleep(min(remaining - self._SPINWAIT_S, self._REFRESH_S))
            else:
                while time.monotonic() < target:
                    if self.cancel.is_set():
                        return
                return
