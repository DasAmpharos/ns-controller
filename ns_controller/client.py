import httpx

from ns_controller.controller import ControllerInput


class NsControllerClient:
    def __init__(self, host: str, port: int, scheme: str = "http") -> None:
        self.client = httpx.Client(base_url=f"{scheme}://{host}:{port}", timeout=None)

    def send_input(self, controller_input: ControllerInput, down: float = 0.1, up: float = 0.1) -> None:
        self.client.post("/update", params={"down": down, "up": up}, json=controller_input.model_dump())