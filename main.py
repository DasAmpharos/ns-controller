import os.path
import time

import click
from fastapi import FastAPI, HTTPException

from ns_controller.controller import Controller, ControllerInput

target = "/dev/hidg0"
controller = Controller()
controller.connect(target)

app = FastAPI()


@app.post('/update')
def update(new_input: ControllerInput):
    previous_input = controller.controller_input
    controller.controller_input = ControllerInput(
        buttons=previous_input.buttons.model_copy(update=new_input.buttons.model_dump()),
        sticks=previous_input.sticks.model_copy(update=new_input.sticks.model_dump()),
        dpad=previous_input.dpad.model_copy(update=new_input.dpad.model_dump())
    )
    return {
        "status": "success",
        "previous_input": previous_input.model_dump()
    }
