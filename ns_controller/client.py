"""Client for connecting to ns-controller server."""

import socket
from typing import Optional

from .protocol import (
    MessageType,
    InputRequestStruct,
    ControllerInput,
)


class Client:
    """Client for sending controller inputs to ns-controller server."""

    def __init__(self, host: str = "raspberrypi.local", port: int = 9000):
        """
        Initialize client connection.

        Args:
            host: Hostname or IP address of the server
            port: TCP port number
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self._connect()

    def _connect(self):
        """Establish connection to the server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

    def close(self):
        """Close the connection."""
        if self.socket:
            self.socket.close()
            self.socket = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def ping(self) -> str:
        """
        Send a ping to the server.

        Returns:
            Server response (should be "PONG")
        """
        self.socket.send(bytes([MessageType.PING]))
        response = self.socket.recv(4)
        return response.decode()

    def send_input(
        self,
        controller_input: ControllerInput,
        down: float = 0.1,
        up: float = 0.1
    ) -> str:
        """
        Send controller input to the server.

        Args:
            controller_input: The controller input state
            down: How long to hold the input in seconds
            up: How long to wait after releasing in seconds

        Returns:
            Server response (should be "OK")
        """
        # Pack the input request
        buttons = controller_input.buttons
        sticks = controller_input.sticks
        dpad = controller_input.dpad

        data = InputRequestStruct.pack(
            int(buttons.a),
            int(buttons.b),
            int(buttons.x),
            int(buttons.y),
            int(buttons.l),
            int(buttons.r),
            int(buttons.zl),
            int(buttons.zr),
            int(buttons.plus),
            int(buttons.minus),
            int(buttons.capture),
            int(buttons.home),
            sticks.left.x,
            sticks.left.y,
            int(sticks.left.pressed),
            sticks.right.x,
            sticks.right.y,
            int(sticks.right.pressed),
            int(dpad.up),
            int(dpad.down),
            int(dpad.left),
            int(dpad.right),
            down,
            up,
        )

        # Send message type and data
        self.socket.send(bytes([MessageType.INPUT]) + data)

        # Wait for response
        response = self.socket.recv(2)
        return response.decode()

