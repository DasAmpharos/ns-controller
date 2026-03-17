import click

from ns_controller.client import MacroBuilder, NsControllerClient
from ns_controller.client_transport import NsControllerGrpcTransport
from ns_controller.pb.ns_controller_pb2 import Button
from ns_controller.server import DEFAULT_PORT


@click.command()
@click.option("--host", default="[::]", show_default=True, help="Server host")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int, help="Server port")
def main(host: str, port: int) -> None:
    macro = (
        MacroBuilder()
        .click(Button.A)
        .wait(20855)
        .mark("hold_start")
        .hold(Button.A, duration_ms=3000)
        .wait_until("hold_start", offset_ms=20645)
        .spam(Button.B, duration_ms=3000)
        .click(Button.A, count=3)
        .mark("final")
        .wait_until("final", offset_ms=5000)
        .click(Button.A)
        .build()
    )

    transport = NsControllerGrpcTransport(host, port)
    client = NsControllerClient(transport)

    print(f"Sending macro to {host}:{port}...")
    for event in client.run_macro(macro):
        print(f"  [{event.action_index}] {event.description}")
        if event.error:
            print(f"  ERROR: {event.error_message}")
            break
        if event.completed:
            break


if __name__ == "__main__":
    main()
