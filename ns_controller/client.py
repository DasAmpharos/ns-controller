import time

import grpc

from ns_controller.pb.ns_controller_pb2 import ControllerState, Button
from ns_controller.pb.ns_controller_pb2_grpc import NsControllerStub


class NsControllerClient:
    def __init__(self, host: str, port: int) -> None:
        self.current_state = ControllerState(buttons=0)
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = NsControllerStub(self.channel)

    def _update_buttons(self, buttons: list[Button], pressed: bool) -> None:
        """
        Helper to set or clear button bits in the mask.
        Args:
            buttons: List of buttons to update
            pressed: True to press, False to release
        """
        for button in buttons:
            if pressed:
                self.current_state.buttons |= (1 << button)
            else:
                self.current_state.buttons &= ~(1 << button)

    def press(self, buttons: list[Button], send: bool = True, post_delay: float | None = 0.1) -> None:
        """
        Press buttons (adds to currently pressed buttons).
        Args:
            buttons: List of buttons to press
            send: If True, immediately send the state to the server
            post_delay: Optional delay in seconds after pressing the buttons
        """
        self._update_buttons(buttons, True)
        if send:
            self.stub.SetState(self.current_state)
        if post_delay:
            time.sleep(post_delay)

    def release(self, buttons: list[Button], send: bool = True, post_delay: float | None = 0.1) -> None:
        """
        Release buttons (removes from currently pressed buttons).
        Args:
            buttons: List of buttons to release
            send: If True, immediately send the state to the server
            post_delay: Optional delay in seconds after releasing the buttons
        """
        self._update_buttons(buttons, False)
        if send:
            self.stub.SetState(self.current_state)
        if post_delay:
            time.sleep(post_delay)

    def click(self, buttons: list[Button], down: float = 0.1, post_delay: float | None = 0.1) -> None:
        """
        Simulate a button click (press and release after a delay).
        Args:
            buttons: List of buttons to click
            down: Time in seconds to hold the buttons down
            post_delay: Optional delay in seconds after releasing the buttons
        """
        self.press(buttons, send=True, post_delay=None)
        time.sleep(down)
        self.release(buttons, send=True, post_delay=None)
        if post_delay:
            time.sleep(post_delay)

    def set_stick(self,
                  ls_x: float = 0.0, ls_y: float = 0.0,
                  rs_x: float = 0.0, rs_y: float = 0.0,
                  send: bool = True,
                  post_delay: float | None = 0.1) -> None:
        """
        Set analog stick positions (range -1.0 to 1.0).
        Args:
            ls_x: Left stick X axis (-1.0 to 1.0)
            ls_y: Left stick Y axis (-1.0 to 1.0)
            rs_x: Right stick X axis (-1.0 to 1.0)
            rs_y: Right stick Y axis (-1.0 to 1.0)
            send: If True, immediately send the state to the server
            post_delay: Optional delay in seconds after setting the sticks
        """
        self.current_state.ls.x = ls_x
        self.current_state.ls.y = ls_y
        self.current_state.rs.x = rs_x
        self.current_state.rs.y = rs_y
        if send:
            self.stub.SetState(self.current_state)
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
        self.current_state.CopyFrom(controller_state)
        if send:
            self.stub.SetState(self.current_state)
        if post_delay:
            time.sleep(post_delay)

    def update_state(self,
                     buttons_press: list[Button] | None = None,
                     buttons_release: list[Button] | None = None,
                     ls_x: float | None = None,
                     ls_y: float | None = None,
                     rs_x: float | None = None,
                     rs_y: float | None = None,
                     send: bool = True,
                     post_delay: float | None = 0.1) -> None:
        """
        Update multiple aspects of the controller state at once.
        Args:
            buttons_press: Buttons to press (adds to current state)
            buttons_release: Buttons to release (removes from current state)
            ls_x: Left stick X position (if specified)
            ls_y: Left stick Y position (if specified)
            rs_x: Right stick X position (if specified)
            rs_y: Right stick Y position (if specified)
            send: If True, immediately send the state to the server
            post_delay: Optional delay in seconds after updating the state
        """
        if buttons_press:
            self._update_buttons(buttons_press, True)
        if buttons_release:
            self._update_buttons(buttons_release, False)
        if ls_x is not None:
            self.current_state.ls.x = ls_x
        if ls_y is not None:
            self.current_state.ls.y = ls_y
        if rs_x is not None:
            self.current_state.rs.x = rs_x
        if rs_y is not None:
            self.current_state.rs.y = rs_y
        if send:
            self.stub.SetState(self.current_state)
        if post_delay:
            time.sleep(post_delay)

    def clear(self, post_delay: float | None = 0.1):
        """
        Clear all inputs (buttons and sticks).
        Args:
            post_delay: Optional delay in seconds after clearing the state
        """
        self.current_state = ControllerState()
        self.stub.SetState(self.current_state)
        if post_delay:
            time.sleep(post_delay)

    def close(self):
        """Close the gRPC channel."""
        self.channel.close()
