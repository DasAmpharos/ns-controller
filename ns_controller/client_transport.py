from collections.abc import Generator
from typing import Protocol

import grpc

from ns_controller.pb.ns_controller_pb2 import ControllerState, Macro, MacroEvent
from ns_controller.pb.ns_controller_pb2_grpc import NsControllerStub


class NsControllerTransport(Protocol):
    def send(self, state: ControllerState) -> None: ...

    def run_macro(self, macro: Macro) -> Generator[MacroEvent, None, None]: ...

    def close(self): ...


class NsControllerGrpcTransport(NsControllerTransport):
    def __init__(self, host: str, port: int) -> None:
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = NsControllerStub(self.channel)

    def send(self, state: ControllerState) -> None:
        self.stub.SetState(state)

    def run_macro(self, macro: Macro) -> Generator[MacroEvent, None, None]:
        yield from self.stub.RunMacro(macro)

    def close(self):
        pass
