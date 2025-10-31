import os.path
import time

import click
from fastapi import FastAPI, HTTPException

from ns_controller.controller import Controller, ControllerInput


@click.command()
@click.option("--filepath", default="/dev/hidg0", help="Path to the controller device file")
def main(filepath: str) -> None:
    """
    Nintendo Switch Controller Server

    Starts a synchronous TCP server for controller input.
    """
    if not os.path.exists(filepath):
        raise click.ClickException(f"Filepath does not exist: {filepath}")

    controller = Controller()
    controller.connect(filepath)

    app = FastAPI()

    @app.post('/update')
    def update(new_input: ControllerInput,
               down: float = 0.1,
               up: float = 0.1):
        try:
            # Capture the previous state, update to new state
            previous_input = controller.controller_input
            controller.controller_input = new_input
            time.sleep(down)
            # Return to the previous state
            controller.controller_input = previous_input
            time.sleep(up)
            return {
                "status": "success"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    main()