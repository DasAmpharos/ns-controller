from collections.abc import Generator
from typing import Protocol

import grpc

from ns_controller.controller import Controller
from ns_controller.pb.ns_controller_pb2 import ControllerState, Macro, MacroEvent
from ns_controller.pb.ns_controller_pb2_grpc import NsControllerStub


class NsControllerTransport(Protocol):
    def send(self, state: ControllerState) -> None: ...

    def run_macro(self, macro: Macro) -> Generator[MacroEvent, None, None]: ...

    def close(self): ...


class NsControllerNativeTransport(NsControllerTransport):
    def __init__(self, controller: Controller) -> None:
        self.controller = controller

    def send(self, state: ControllerState) -> None:
        self.controller.state.CopyFrom(state)

    def run_macro(self, macro: Macro) -> Generator[MacroEvent, None, None]:
        raise NotImplementedError("RunMacro is not supported on native transport")

    def close(self):
        self.controller.close()


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
