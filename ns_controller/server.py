from concurrent import futures
from concurrent import futures
from typing import Final

import click
import grpc
from google.protobuf.empty_pb2 import Empty

from ns_controller.controller import Controller
from ns_controller.pb.ns_controller_pb2 import ClickRequest, ControllerState, PressRequest, ReleaseRequest, \
    StickRequest
from ns_controller.pb.ns_controller_pb2_grpc import NsControllerServicer, add_NsControllerServicer_to_server
from ns_controller.state import EnhancedControllerState

DEFAULT_HID_PATH: Final = "/dev/hidg0"
DEFAULT_HOST: Final = "[::]"
DEFAULT_PORT: Final = 50051


class NsControllerServicerImpl(NsControllerServicer):
    EMPTY: Final = Empty()

    def __init__(self, hid_path: str = DEFAULT_HID_PATH):
        self.state = EnhancedControllerState()
        self.controller = Controller(self.state.proto)
        self.controller.connect(hid_path)

    def Click(self, request: ClickRequest, context):
        return self.state.click(*request.buttons, duration=request.duration or 0.1)

    def Press(self, request: PressRequest, context):
        return self.state.press(*request.buttons)

    def Release(self, request: ReleaseRequest, context):
        return self.state.release(*request.buttons)

    def SetStick(self, request: StickRequest, context):
        return self.state.set_stick(request.stick, request.position)

    def SetState(self, request: ControllerState, context):
        return self.state.set_state(request)

    def GetState(self, request: Empty, context):
        return self.state.proto

    def Clear(self, request: Empty, context):
        return self.state.clear()


@click.command()
@click.option("--hid-path", default=DEFAULT_HID_PATH, help="The path to the HID gadget device.")
@click.option("--host", type=str, default=DEFAULT_HOST, help="The host to listen on.")
@click.option("--port", type=int, default=DEFAULT_PORT, help="The port to listen on.")
def cli(hid_path: str, host: str, port: int):
    server = main(hid_path, host, port)
    server.wait_for_termination()


def main(hid_path: str = DEFAULT_HID_PATH, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_NsControllerServicer_to_server(NsControllerServicerImpl(hid_path), server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    return server


if __name__ == '__main__':
    cli()
