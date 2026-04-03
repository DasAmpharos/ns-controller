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


@click.group()
def main() -> None:
    pass


@main.command("run")
@click.option("--host", default="[::]", show_default=True, help="Server host")
@click.option("--port", default=DEFAULT_PORT, show_default=True, type=int, help="Server port")
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging level.")
def run(host: str, port: int, log_level: str) -> None:
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
        .wait_until("phase_1", offset_ms=30458 + 52) # + 58
        .hold(Button.A, mark="phase_2", duration_ms=5000)
        .wait_until("phase_2", offset_ms=round(2759 * GBA_FRAME_MS) + 2553 - 7838 + round(9 * GBA_FRAME_MS)) # + round(2 * GBA_FRAME_MS)) # 2530,2477
        .click(Button.A, mark="phase_3")
        .spam(Button.B, duration_ms=3500, interval_ms=150)
        # .spam(Button.A, duration_ms=3000, interval_ms=150)
        .click(Button.X)
        .wait(300)
        .click(Button.DPAD_DOWN)
        .wait(300)
        .click(Button.A)
        .wait(1250)
        .click(Button.A)
        .wait(300)
        .click(Button.DPAD_DOWN)
        .wait(300)
        .wait_until("phase_3", offset_ms=round(500 * GBA_FRAME_MS))
        .click(Button.A)
        .build()
    )

# 2662

    # macro = (
    #     MacroBuilder()
    #     .click(Button.A, mark="start")
    #     .wait_until("start", offset_ms=round(1500 * GBA_FRAME_MS))
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


@main.command("calibrate")
@click.argument("target", type=float)
@click.argument("actual", type=float)
@click.option("--current-cal", default=0.0, show_default=True, type=float,
              help="Your current calibration constant in ms.")
@click.option("--ms", "use_ms", is_flag=True, default=False,
              help="Treat TARGET and ACTUAL as milliseconds instead of frames.")
def calibrate(target: float, actual: float, current_cal: float, use_ms: bool) -> None:
    """Compute a corrected calibration offset from a missed advance.

    TARGET is the advance you were aiming for.
    ACTUAL is the advance you hit.

    Example (frames): python run_macro.py calibrate 5835 6329 --current-cal 2486
    Example (ms):     python run_macro.py calibrate 97.3 105.6 --ms --current-cal 2486
    """
    if use_ms:
        delta_ms = actual - target
        new_cal = current_cal - delta_ms
        direction = "late" if delta_ms > 0 else "early"
        print(f"Hit {actual} ms, aimed for {target} ms: {abs(delta_ms):.2f} ms {direction}")
        print(f"New calibration: {new_cal:.2f}  (was {current_cal:.2f})")
    else:
        delta_frames = actual - target
        delta_ms = delta_frames * GBA_FRAME_MS
        new_cal = current_cal - delta_ms
        direction = "late" if delta_frames > 0 else "early"
        print(f"Hit {actual:.0f}, aimed for {target:.0f}: {abs(delta_frames):.0f} frames {direction} ({delta_ms:+.2f} ms)")
        print(f"New calibration: {new_cal:.2f}  (was {current_cal:.2f})")


if __name__ == "__main__":
    main()
