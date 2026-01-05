from ns_controller.client.transport.transport import NsControllerTransport
from ns_controller.controller import Controller
from ns_controller.pb.ns_controller_pb2 import ControllerState


class NsControllerNativeTransport(NsControllerTransport):
    def __init__(self, controller: Controller) -> None:
        self.controller = controller

    def send(self, state: ControllerState) -> None:
        self.controller.state.CopyFrom(state)

    def close(self):
        pass