from ns_controller.client import NsControllerClient
from ns_controller.controller import ControllerInput

client = NsControllerClient('ns-controller.local', 8000)
client.send_input(ControllerInput(dpad=ControllerInput.DPad(up=True)), down=0.5)
