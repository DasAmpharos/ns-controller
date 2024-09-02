import time

from fastapi import FastAPI

from ns_controller import NsController

target = "/dev/hidg0"
controller = NsController()
controller.connect(target)

app = FastAPI()


@app.post('/update')
def update(inputs: NsController.InputStruct,
           down: float = 0.1,
           up: float = 0.1):
    temp = controller.inputs
    controller.inputs = inputs
    time.sleep(down)
    controller.inputs = temp
    time.sleep(up)
    return {
        "status": "success"
    }
