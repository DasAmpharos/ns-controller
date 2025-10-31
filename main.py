import time

from fastapi import FastAPI

from ns_controller.controller import Controller, ControllerInput

target = "/dev/hidg0"
controller = Controller()
controller.connect(target)

app = FastAPI()


@app.post('/update')
def update(new_input: ControllerInput,
           down: float = 0.1,
           up: float = 0.1):
    previous_input = controller.controller_input
    controller.controller_input = new_input
    time.sleep(down)
    controller.controller_input = previous_input
    time.sleep(up)
    return {
        "status": "success"
    }
