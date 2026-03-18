import sys
import threading
from concurrent import futures
from typing import Final

import click
import grpc
from google.protobuf.empty_pb2 import Empty
from loguru import logger

from ns_controller.controller import Controller
from ns_controller.macro_executor import MacroExecutor
from ns_controller.pb.ns_controller_pb2 import (
    ClickRequest,
    ControllerState,
    Macro,
    PressRequest,
    ReleaseRequest,
    StickRequest,
)
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
        self.state.set_notify(self.controller.trigger_report)
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

    def RunMacro(self, request: Macro, context):
        cancel = threading.Event()
        context.add_callback(cancel.set)

        def run_executor():
            for event in MacroExecutor(request, self.state, cancel).execute():
                logger.info(f"[macro] action={event.action_index} {event.description}")

        logger.info(f"Starting macro with {len(request.actions)} actions")
        thread = threading.Thread(target=run_executor, daemon=True)
        thread.start()
        thread.join()
        logger.info("Macro execution finished")
        return iter([])


@click.command()
@click.option("--hid-path", default=DEFAULT_HID_PATH, help="The path to the HID gadget device.")
@click.option("--host", type=str, default=DEFAULT_HOST, help="The host to listen on.")
@click.option("--port", type=int, default=DEFAULT_PORT, help="The port to listen on.")
@click.option("--mock", is_flag=True, default=False, help="Run in mock mode (no HID device).")
@click.option("--gamepad", type=str, default=None, help="Path to evdev gamepad device (e.g. /dev/input/event0).")
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging level.")
def cli(hid_path: str, host: str, port: int, mock: bool, gamepad: str | None, log_level: str):
    logger.remove()
    logger.add(sys.stderr, level=log_level.upper(), enqueue=True)
    server = main(hid_path, host, port, mock=mock, gamepad=gamepad)
    server.wait_for_termination()


def main(
    hid_path: str = DEFAULT_HID_PATH,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    mock: bool = False,
    gamepad: str | None = None,
) -> grpc.Server:
    servicer = NsControllerServicerImpl(hid_path="/dev/null" if mock else hid_path)

    if gamepad:
        try:
            from ns_controller.gamepad_input import GamepadInput

            gamepad_input = GamepadInput(servicer.state, device_path=gamepad)
            gamepad_input.start()
            logger.info(f"Gamepad input started on {gamepad}")
        except ImportError:
            logger.warning("evdev not installed — gamepad input disabled")
        except Exception as e:
            logger.error(f"Failed to start gamepad input: {e}")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_NsControllerServicer_to_server(servicer, server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    logger.info(f"Server started on {host}:{port}")
    return server


if __name__ == "__main__":
    cli()
