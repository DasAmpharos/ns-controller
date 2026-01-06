import code

import click

from ns_controller.client import NsControllerClient
from ns_controller.client.transport.grpc import NsControllerGrpcTransport
from ns_controller.client.transport.native import NsControllerNativeTransport
from ns_controller.client.transport.transport import NsControllerTransport
from ns_controller.controller import Controller
from ns_controller.pb.ns_controller_pb2 import Button
from ns_controller.server import DEFAULT_HOST, DEFAULT_PORT


@click.group()
def cli():
    pass


@cli.command()
@click.option("--host", default=DEFAULT_HOST, help="Server host")
@click.option("--port", default=DEFAULT_PORT, type=int, help="Server port")
def grpc(host: str, port: int) -> None:
    main(NsControllerGrpcTransport(host, port))


@cli.command()
@click.option("--hid-path", default="/dev/hidg0")
def native(hid_path: str) -> None:
    controller = Controller()
    controller.connect(hid_path)
    main(NsControllerNativeTransport(controller))

def main(transport: NsControllerTransport):
    client = NsControllerClient(transport)
    code.interact(local={
        "controller": client,

        "UP": Button.DPAD_UP,
        "DOWN": Button.DPAD_DOWN,
        "LEFT": Button.DPAD_LEFT,
        "RIGHT": Button.DPAD_RIGHT,
        **{name: value for name, value in Button.items()},

        "click": client.click,
        "set_stick": client.set_stick,
        "clear": client.clear,
    })

if __name__ == '__main__':
    cli()
