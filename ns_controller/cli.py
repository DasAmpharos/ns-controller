import argparse
import asyncio
import logging
import os.path

from ns_controller.logging import LogLevel, setup_logging
from .controller import Controller
from .server import Server


def cli() -> None:
    """
    Nintendo Switch Controller Server

    Starts a TCP server for controller input.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--filepath", default="/dev/hidg0")
    parser.add_argument("--host", default="0.0.0.0", help="TCP server host")
    parser.add_argument("--port", type=int, default=9000, help="TCP server port")
    parser.add_argument("--log-level", default=LogLevel.INFO, choices=list(LogLevel), help="Log level")
    args = parser.parse_args()

    setup_logging(args.log_level)
    exit(asyncio.run(main(args.filepath, args.host, args.port)))


async def main(filepath: str, host: str, port: int) -> int:
    logger = logging.getLogger("ns_controller.cli")

    if not os.path.exists(filepath):
        logger.error(f"Filepath does not exist: {filepath}")
        return 1

    controller = Controller()
    await controller.connect(filepath)

    server = Server(controller)
    socket_server = await asyncio.start_server(server.handle_client, host, port)
    logger.info(f"Server listening on {host}:{port}")
    async with socket_server:
        await socket_server.serve_forever()
    return 0


if __name__ == "__main__":
    cli()
