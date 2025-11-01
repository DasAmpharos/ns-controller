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
    controller.controller_input = new_input
    return {
        "status": "success",
        "previous_input": previous_input.model_dump()
    }
