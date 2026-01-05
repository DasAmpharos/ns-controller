from typing import Protocol

import grpc

from ns_controller.controller import Controller
from ns_controller.pb.ns_controller_pb2 import ControllerState
from ns_controller.pb.ns_controller_pb2_grpc import NsControllerStub


class NsControllerTransport(Protocol):
    def send(self, state: ControllerState) -> None:
        ...

    def close(self):
        ...


class NsControllerGrpcTransport(NsControllerTransport):
    def __init__(self, host: str, port: int) -> None:
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = NsControllerStub(self.channel)

    def send(self, state: ControllerState) -> None:
        self.stub.SetState(state)

    def close(self):
        """Close the gRPC channel."""
        self.channel.close()


class NsControllerNativeTransport(NsControllerTransport):
    def __init__(self, controller: Controller) -> None:
        self.controller = controller

    def send(self, state: ControllerState) -> None:
        self.controller.state.CopyFrom(state)

    def close(self):
        self.controller.close()
