import code

import click

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_controller.server import DEFAULT_HOST, DEFAULT_PORT


@click.command()
@click.option("--host", default=DEFAULT_HOST, help="Server host")
@click.option("--port", default=DEFAULT_PORT, type=int, help="Server port")
def main(host: str, port: int) -> None:
    client = NsControllerClient(host, port)
    namespace = {
        "UP": Button.DPAD_UP,
        "DOWN": Button.DPAD_DOWN,
        "LEFT": Button.DPAD_LEFT,
        "RIGHT": Button.DPAD_RIGHT,
        **{name: value for name, value in Button.items()}
    }
    code.interact(local={
        "controller": client,
        "click": client.click,
        **namespace
    })


if __name__ == '__main__':
    main()
