from concurrent import futures
from typing import Final

import click
import grpc

from ns_controller.controller import Controller
from ns_controller.pb.ns_controller_pb2 import ControllerState, Ack
from ns_controller.pb.ns_controller_pb2_grpc import NsControllerServicer, add_NsControllerServicer_to_server

DEFAULT_HOST: Final = "[::]"
DEFAULT_PORT: Final = 50051


class NsControllerServicerImpl(NsControllerServicer):
    def __init__(self):
        self.controller = Controller()
        self.controller.connect("/dev/hidg0")

    def SetState(self, request: ControllerState, context):
        # Implement your logic to handle SetState requests here
        previous_state = self.controller.state
        self.controller.state = request
        return Ack(
            success=True,
            previous_state=previous_state
        )

    def StreamState(self, request_iterator, context):
        # Implement your logic to handle StreamState requests here
        for request in request_iterator:
            yield self.SetState(request, context)


@click.command()
@click.option("--host", type=str, default=DEFAULT_HOST, help="The host to listen on.")
@click.option("--port", type=int, default=DEFAULT_PORT, help="The port to listen on.")
def cli(host: str, port: int):
    server = main(host, port)
    server.wait_for_termination()


def main(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_NsControllerServicer_to_server(NsControllerServicerImpl(), server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    return server


if __name__ == '__main__':
    cli()
