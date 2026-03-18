import sys

import click

from ns_controller.client import MacroBuilder, NsControllerClient
from ns_controller.client_transport import NsControllerGrpcTransport
from ns_controller.pb.ns_controller_pb2 import Button
from ns_controller.server import DEFAULT_PORT

from loguru import logger
import math
import time

GBA_FRAMERATE = 16777216 / 280896
GBA_FRAME_MS = 1000 / GBA_FRAMERATE


@click.command()
@click.option("--host", default="[::]", show_default=True, help="Server host")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int, help="Server port")
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging level.")
def main(host: str, port: int, log_level: str) -> None:
    logger.remove()
    logger.add(sys.stderr, level=log_level.upper(), enqueue=True)
    macro = (
        MacroBuilder()
        .click(Button.HOME)
        .wait(1500)
        .click(Button.X)
        .wait(1500)
        .click(Button.A)
        .wait(1000)
        .click(Button.A)
        .wait(1000)
        .click(Button.A)
        .wait(250)
        .click(Button.HOME)
        .wait(3500)
        .click(Button.A, down_ms=50, mark="phase_1")
        .wait_until("phase_1", offset_ms=29989 + 52) # + 58
        .hold(Button.A, mark="phase_2", duration_ms=5000)
        .wait_until("phase_2", offset_ms=round(251 * GBA_FRAME_MS) + 2489 + round(4 * GBA_FRAME_MS)) # + round(2 * GBA_FRAME_MS)) # 2530,2477
        .click(Button.A, mark="phase_3")
        .spam(Button.B, duration_ms=3000, interval_ms=150)
        .spam(Button.A, duration_ms=3000, interval_ms=150)
        .wait_until("phase_3", offset_ms=round(478 * GBA_FRAME_MS))
        .click(Button.A)
        .build()
    )

    # macro = (
    #     MacroBuilder()
    #     .mark("start")
    #     .click(Button.A)
    #     .wait_until("start", offset_ms=round(1500 * GBA_FRAMERATE))
    #     .click(Button.A)
    #     .build()
    # )

    transport = NsControllerGrpcTransport(host, port)
    client = NsControllerClient(transport)

    print(f"Sending macro to {host}:{port}...")
    for event in client.run_macro(macro):
        logger.info(f"[{event.action_index}] {event.description}")
        if event.error:
            print(f"  ERROR: {event.error_message}")
            break
        if event.completed:
            break


if __name__ == "__main__":
    main()
