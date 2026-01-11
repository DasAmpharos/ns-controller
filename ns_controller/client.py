import time

from .client_transport import NsControllerTransport
from ns_controller.pb.ns_controller_pb2 import ControllerState, Button, Position, Stick
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