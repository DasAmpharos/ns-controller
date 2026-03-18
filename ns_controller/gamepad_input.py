"""Read a USB gamepad via evdev and write inputs to the shared controller state.

Linux-only (requires the `evdev` package). The import is guarded in server.py
so the rest of the project works without it.
"""

import threading
from typing import Final

from loguru import logger

try:
    import evdev
    from evdev import InputDevice, ecodes
except ImportError as _exc:
    raise ImportError("evdev is required for gamepad input: pip install evdev") from _exc

from ns_controller.pb.ns_controller_pb2 import Position, Stick
from ns_controller.state import EnhancedControllerState

DEFAULT_STICK_DEADZONE: Final[float] = 0.05

# Default mapping: evdev button code -> Button bit position.
# Matches a standard Pro Controller / Xbox-style USB gamepad.
# Run `evtest` on the Pi to discover the codes for your specific gamepad.
DEFAULT_BUTTON_MAP: Final[dict[int, int]] = {
    ecodes.BTN_SOUTH: 1,  # B (bottom) — Switch A/B and X/Y are swapped vs Xbox layout
    ecodes.BTN_EAST: 0,   # A (right)
    ecodes.BTN_NORTH: 3,  # Y (top)
    ecodes.BTN_WEST: 2,   # X (left)
    ecodes.BTN_TL: 4,  # L
    ecodes.BTN_TR: 5,  # R
    ecodes.BTN_TL2: 6,  # ZL
    ecodes.BTN_TR2: 7,  # ZR
    ecodes.BTN_THUMBL: 8,  # L_STICK
    ecodes.BTN_THUMBR: 9,  # R_STICK
    ecodes.BTN_START: 10,  # PLUS
    ecodes.BTN_SELECT: 11,  # MINUS
    ecodes.BTN_MODE: 12,  # HOME
}

# Axis mapping: evdev axis code -> (Stick enum, axis name)
DEFAULT_AXIS_MAP: Final[dict[int, tuple[Stick, str]]] = {
    ecodes.ABS_X: (Stick.LS, "x"),
    ecodes.ABS_Y: (Stick.LS, "y"),
    ecodes.ABS_RX: (Stick.RS, "x"),
    ecodes.ABS_RY: (Stick.RS, "y"),
}

# D-pad hat mapping: evdev axis code -> (negative_bit, positive_bit)
DEFAULT_HAT_MAP: Final[dict[int, tuple[int, int]]] = {
    ecodes.ABS_HAT0X: (16, 17),  # DPAD_LEFT=16, DPAD_RIGHT=17
    ecodes.ABS_HAT0Y: (14, 15),  # DPAD_UP=14,   DPAD_DOWN=15  (hat Y: -1=up, +1=down)
}


def find_gamepad() -> str | None:
    """Auto-detect the first gamepad in /dev/input/ that has buttons and axes."""
    for path in evdev.list_devices():
        device = InputDevice(path)
        caps = device.capabilities(verbose=False)
        if ecodes.EV_KEY in caps and ecodes.EV_ABS in caps:
            logger.info(f"Auto-detected gamepad: {device.name} at {device.path}")
            return device.path
    return None


class GamepadInput:
    """Reads USB gamepad events via evdev and writes to EnhancedControllerState."""

    def __init__(
        self,
        state: EnhancedControllerState,
        device_path: str | None = None,
        button_map: dict[int, int] | None = None,
        axis_map: dict[int, tuple[Stick, str]] | None = None,
        hat_map: dict[int, tuple[int, int]] | None = None,
        stick_deadzone: float = DEFAULT_STICK_DEADZONE,
    ):
        if device_path is None:
            device_path = find_gamepad()
        if device_path is None:
            raise RuntimeError("No gamepad device found")

        self.state: Final = state
        self.device: Final = InputDevice(device_path)
        self.button_map: Final = button_map or DEFAULT_BUTTON_MAP
        self.axis_map: Final = axis_map or DEFAULT_AXIS_MAP
        self.hat_map: Final = hat_map or DEFAULT_HAT_MAP
        self.stick_deadzone: Final = stick_deadzone

        self._stop: Final = threading.Event()
        self._thread: Final = threading.Thread(target=self._run, daemon=True)

        # Cache axis info for normalization
        self._axis_info: dict[int, tuple[int, int]] = {}
        caps = self.device.capabilities(absinfo=True)
        for code, absinfo in caps.get(ecodes.EV_ABS, []):
            self._axis_info[code] = (absinfo.min, absinfo.max)

        # Local stick positions accumulated across axis events in a sync frame.
        # Flushed directly to state.proto on EV_SYN (without notify) so stick
        # movement does not flood the report thread with immediate triggers.
        # Button events (EV_KEY, hat) still go through press()/release() and
        # do trigger immediate reports — they are discrete and timing-critical.
        self._ls = Position(x=0.0, y=0.0)
        self._rs = Position(x=0.0, y=0.0)
        self._ls_dirty = False
        self._rs_dirty = False

        logger.info(f"GamepadInput initialized: {self.device.name} ({device_path})")

    def start(self) -> None:
        self._stop.clear()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        try:
            for event in self.device.read_loop():
                if self._stop.is_set():
                    return

                if event.type == ecodes.EV_KEY:
                    self._handle_button(event.code, event.value)
                elif event.type == ecodes.EV_ABS:
                    self._handle_axis(event.code, event.value)
                elif event.type == ecodes.EV_SYN:
                    self._flush_sticks()
        except OSError as e:
            logger.error(f"Gamepad disconnected: {e}")
        except Exception as e:
            logger.exception(f"GamepadInput thread crashed: {e}")

    def _flush_sticks(self) -> None:
        """Write accumulated stick positions directly to proto without notify.

        Stick movement is continuous; the 8ms HID keepalive is sufficient to
        deliver updated stick state. Bypassing notify prevents a trigger_report()
        call (and thus an immediate HID send) on every EV_SYN event.
        """
        if self._ls_dirty:
            self.state.proto.ls.CopyFrom(self._ls)
            self._ls_dirty = False
        if self._rs_dirty:
            self.state.proto.rs.CopyFrom(self._rs)
            self._rs_dirty = False

    def _handle_button(self, code: int, value: int) -> None:
        bit = self.button_map.get(code)
        if bit is None:
            return
        if value:
            self.state.press(bit)
        else:
            self.state.release(bit)

    def _handle_axis(self, code: int, value: int) -> None:
        if code in self.hat_map:
            # Hat events are discrete (button-like) — trigger immediate report.
            neg_bit, pos_bit = self.hat_map[code]
            self.state.release(neg_bit, pos_bit)
            if value < 0:
                self.state.press(neg_bit)
            elif value > 0:
                self.state.press(pos_bit)
            return

        mapping = self.axis_map.get(code)
        if mapping is None:
            return

        stick_enum, axis = mapping
        normalized = self._normalize_axis(code, value)
        # Y axis is inverted on most gamepads (up = negative raw value)
        if axis == "y":
            normalized = -normalized

        # Apply center deadzone — snaps small values to 0.0 to suppress noise
        if abs(normalized) < self.stick_deadzone:
            normalized = 0.0

        pos = self._ls if stick_enum == Stick.LS else self._rs
        old = pos.x if axis == "x" else pos.y
        if normalized == old:
            return

        if axis == "x":
            pos.x = normalized
        else:
            pos.y = normalized

        if stick_enum == Stick.LS:
            self._ls_dirty = True
        else:
            self._rs_dirty = True

    def _normalize_axis(self, code: int, value: int) -> float:
        info = self._axis_info.get(code)
        if info is None:
            return 0.0
        axis_min, axis_max = info
        if axis_max == axis_min:
            return 0.0
        return 2.0 * (value - axis_min) / (axis_max - axis_min) - 1.0
