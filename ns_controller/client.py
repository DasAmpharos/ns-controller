import httpx

from ns_controller.controller import ControllerInput


class NsControllerClient:
    def __init__(self, host: str, port: int, scheme: str = "http") -> None:
        self.client = httpx.Client(base_url=f"{scheme}://{host}:{port}", timeout=None)

    def send_input(self, controller_input: ControllerInput, down: float | None = None) -> None:
        params = {}
        if down is not None and down > 0:
            params["down"] = down
        self.client.post("/update", params=params, json=controller_input.model_dump())