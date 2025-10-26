import asyncio
import subprocess
from pathlib import Path

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
    client_proc = None
    try:
        client_proc = start_client()
        await start_server(filepath, host, port)
    finally:
        if client_proc and client_proc.poll() is None:
            client_proc.terminate()
            try:
                client_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                client_proc.kill()
                client_proc.wait()


def start_client() -> subprocess.Popen[bytes] | None:
    # Start Streamlit UI as a subprocess
    try:
        # Keep stdout/stderr visible for Streamlit since it shows the URL
        client_proc = subprocess.Popen([
            # Optimize Streamlit for low-resource environments
            "streamlit", "run", str(Path(__file__).parent / "client.py"),
            "--server.headless", "true",  # No browser auto-open
            "--server.runOnSave", "false",  # Disable file watcher
            "--browser.gatherUsageStats", "false",  # Disable telemetry
        ])
        logger.info(f"Streamlit UI started (PID: {client_proc.pid})")
        return client_proc
    except FileNotFoundError:
        logger.warning("streamlit not found, UI not started")
        return None


async def start_server(filepath: str, host: str, port: int):
    controller = Controller()
    await controller.connect(filepath)

    server_instance: Server = Server(controller)
    server = await asyncio.start_server(server_instance.client_connected, host, port)
    logger.info(f"Server listening on {host}:{port}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    main()
