import os.path
import time

import click
from fastapi import FastAPI, HTTPException

from .controller import Controller, ControllerInput


@click.command()
@click.option("--filepath", default="/dev/hidg0", help="Path to the controller device file")
def main(filepath: str) -> None:
    """
    Nintendo Switch Controller - connects to USB gadget and handles controller protocol.

    The process will run until interrupted (Ctrl+C).
    """
    if not os.path.exists(filepath):
        raise click.ClickException(f"Filepath does not exist: {filepath}")

    controller = Controller()
    controller.connect(filepath)

    click.echo(f"Controller connected to {filepath}")
    click.echo("Press Ctrl+C to stop")

    try:
        # Keep the main thread alive so daemon threads can run
        # This matches Go's behavior where Connect() starts goroutines
        # and the main program blocks until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        controller.close()


if __name__ == "__main__":
    main()
