"""
Client for connecting to ns-controller TCP server
"""

import json
import socket
import struct
from enum import IntEnum

from .controller import Buttons, ControllerState


class MessageType(IntEnum):
    PING = 0
    NORMAL = 1
    GET_STATE = 2
    MACRO_START = 3
    MACRO_STOP = 4
    PAUSE_MACRO = 5
    RESUME_MACRO = 6
    LIST_MACROS = 7
    LOAD_MACRO = 8
    SAVE_MACRO = 9
    DELETE_MACRO = 10
    GET_MACRO_STATUS = 11


class Client:
    """Client for connecting to ns-controller server"""

    def __init__(self, host: str = "localhost", port: int = 9000):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        """Connect to the server"""
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))

    def close(self):
        """Close the connection"""
        if self.sock:
            self.sock.close()
            self.sock = None

    def send(self, msg_type: MessageType, payload: bytes = b"") -> bytes:
        """Send a message and return the response"""
        self.sock.send(bytes([msg_type]) + payload)
        return self.sock.recv(4096)

    def ping(self) -> str:
        """Ping the server"""
        self.connect()
        resp = self.send(MessageType.PING)
        self.close()
        return resp.decode()

    def send_state(self, state: ControllerState, down: float = 0.1, up: float = 0.1):
        """Send controller state to the server"""
        self.connect()

        # Pack state: 18 buttons + 2 stick press + 4 stick values + down + up
        buttons_list = []
        for i in range(18):
            buttons_list.append(1 if state.buttons & (1 << i) else 0)

        # Check if LS and RS are pressed (buttons 12 and 13)
        ls_pressed = 1 if state.is_pressed(Buttons.LS) else 0
        rs_pressed = 1 if state.is_pressed(Buttons.RS) else 0

        payload = struct.pack(
            "20B4i2d",
            *buttons_list,
            ls_pressed,
            rs_pressed,
            int(state.ls.x),
            int(state.ls.y),
            int(state.rs.x),
            int(state.rs.y),
            down,
            up,
        )

        resp = self.send(MessageType.NORMAL, payload)
        self.close()
        return resp.decode()

    def get_state(self):
        """Get current controller state from server"""
        self.connect()
        resp = self.send(MessageType.GET_STATE)
        self.close()
        try:
            return json.loads(resp.decode())
        except Exception:
            return None

    def start_macro(self, macro_data, repeat=None):
        """Start a macro. Can be dict, JSON string, or NXBT text."""
        self.connect()
        if isinstance(macro_data, str):
            # It's NXBT text - wrap it in JSON so server can parse it
            # Server will receive a JSON string, then check isinstance(macro_data, str)
            macro_json = json.dumps(macro_data)
        else:
            # It's a dict
            if repeat is not None:
                macro_data["repeat"] = repeat
            macro_json = json.dumps(macro_data)

        macro_bytes = macro_json.encode()
        payload = struct.pack(">I", len(macro_bytes)) + macro_bytes
        resp = self.send(MessageType.MACRO_START, payload)
        self.close()
        return resp.decode()

    def stop_macro(self):
        """Stop the currently running macro"""
        self.connect()
        resp = self.send(MessageType.MACRO_STOP)
        self.close()
        return resp.decode()

    def pause_macro(self):
        """Pause the currently running macro"""
        self.connect()
        resp = self.send(MessageType.PAUSE_MACRO)
        self.close()
        return resp.decode()

    def resume_macro(self):
        """Resume the paused macro"""
        self.connect()
        resp = self.send(MessageType.RESUME_MACRO)
        self.close()
        return resp.decode()

    def list_macros(self):
        """List all saved macros"""
        self.connect()
        resp = self.send(MessageType.LIST_MACROS)
        self.close()
        try:
            return json.loads(resp.decode())
        except Exception:
            return []

    def load_macro(self, name: str):
        """Load a saved macro by name"""
        self.connect()
        name_bytes = name.encode()
        payload = struct.pack(">H", len(name_bytes)) + name_bytes
        resp = self.send(MessageType.LOAD_MACRO, payload)
        self.close()
        try:
            return json.loads(resp.decode())
        except Exception:
            return None

    def save_macro(self, name: str, macro_text: str):
        """Save a macro. Can be NXBT text format or JSON."""
        self.connect()
        name_bytes = name.encode()
        macro_bytes = macro_text.encode()
        payload = struct.pack(">H", len(name_bytes)) + name_bytes + struct.pack(">I", len(macro_bytes)) + macro_bytes
        resp = self.send(MessageType.SAVE_MACRO, payload)
        self.close()
        return resp.decode()

    def delete_macro(self, name: str):
        """Delete a saved macro by name"""
        self.connect()
        name_bytes = name.encode()
        payload = struct.pack(">H", len(name_bytes)) + name_bytes
        resp = self.send(MessageType.DELETE_MACRO, payload)
        self.close()
        return resp.decode()

    def get_macro_status(self):
        """Get the current status of the macro runner"""
        self.connect()
        resp = self.send(MessageType.GET_MACRO_STATUS)
        self.close()
        try:
            return json.loads(resp.decode())
        except Exception:
            return {"running": False, "paused": False}


