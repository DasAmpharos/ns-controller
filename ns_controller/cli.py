import asyncio

import click
from loguru import logger

from .controller import Controller
from .server import Server


@click.command()
@click.option("-f", "--filepath", default="/dev/hidg0")
@click.option("--host", default="0.0.0.0", help="TCP server host")
@click.option("--port", type=int, default=9000, help="TCP server port")
def main(filepath: str, host: str, port: int) -> None:
    """
    Nintendo Switch Controller Server

    Starts a TCP server for controller input and a Streamlit web UI.
    The UI runs as a web server - access it from any browser at http://<pi-ip>:8501
    """
    asyncio.run(amain(filepath, host, port))


async def amain(filepath: str, host: str, port: int):
    controller = Controller()
    await controller.connect(filepath)

    server_instance: Server = Server(controller)
    server = await asyncio.start_server(server_instance.client_connected, host, port)
    logger.info(f"Server listening on {host}:{port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    main()
