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
    def __init__(self, host: str, port: int, timeout: float = 5.0) -> None:
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = NsControllerStub(self.channel)
        self.timeout = timeout

    def send(self, state: ControllerState) -> None:
        self.stub.SetState(state, timeout=self.timeout)

    def run_macro(self, macro: Macro) -> Generator[MacroEvent, None, None]:
        yield from self.stub.RunMacro(macro, timeout=self.timeout)

    def close(self):
        pass
