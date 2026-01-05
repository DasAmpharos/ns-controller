import grpc

from ns_controller.client.transport.transport import NsControllerTransport
from ns_controller.pb.ns_controller_pb2 import ControllerState
from ns_controller.pb.ns_controller_pb2_grpc import NsControllerStub


class NsControllerGrpcTransport(NsControllerTransport):
    def __init__(self, host: str, port: int) -> None:
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = NsControllerStub(self.channel)

    def send(self, state: ControllerState) -> None:
        self.stub.SetState(state)

    def close(self):
        """Close the gRPC channel."""
        self.channel.close()