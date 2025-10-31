import time

from fastapi import FastAPI

from ns_controller.controller import Controller, ControllerInput

target = "/dev/hidg0"
controller = Controller()
controller.connect(target)

app = FastAPI()


@app.post('/update')
def update(new_input: ControllerInput,
           down: float | None = None):
    previous_input = controller.controller_input
    controller.controller_input = new_input
    if down is not None and down > 0:
        time.sleep(down)
        controller.controller_input = previous_input
        time.sleep(0.1)
    return {
        "status": "success"
    }
