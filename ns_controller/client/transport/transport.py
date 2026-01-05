from typing import Protocol

from ns_controller.pb.ns_controller_pb2 import ControllerState, Button


class NsControllerTransport(Protocol):
    def send(self, state: ControllerState) -> None:
        ...

    def close(self):
        ...
