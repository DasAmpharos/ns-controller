import time

import click
from fastapi import FastAPI, HTTPException

from .controller import ControllerState, NsController


@click.command()
@click.option("-f", "--filepath", type=click.Path(exists=True), default="/dev/hidg0")
def main(filepath: str):
    controller = NsController()
    controller.connect(filepath)

    app = FastAPI()

    @app.post('/update')
    def update(new_state: ControllerState,
               down: float = 0.1,
               up: float = 0.1):
        try:
            # Capture the previous state, update to new state
            previous_state = controller.state
            controller.state = new_state
            time.sleep(down)
            # Return to the previous state
            controller.state = previous_state
            time.sleep(up)
            return {
                "status": "success"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    main()
