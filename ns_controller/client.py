import time

import httpx

from ns_controller.controller import ControllerInput


class NsControllerClient:
    def __init__(self, host: str, port: int, scheme: str = "http") -> None:
        self.client = httpx.Client(base_url=f"{scheme}://{host}:{port}", timeout=None)

    def clear(self, up: float | None = 0.1):
        self.client.post("/update", json=ControllerInput().model_dump())
        if up is not None and up > 0:
            time.sleep(up)

    def send_input(self,
                   controller_input: ControllerInput,
                   down: float | None = None,
                   up: float | None = 0.1) -> None:
        resp = self.client.post("/update", json=controller_input.model_dump())
        if down is not None and down > 0:
            resp_body = resp.json()
            previous_input = resp_body["previous_input"]

            time.sleep(down)
            self.client.post("/update", json=previous_input)
        if up is not None and up > 0:
            time.sleep(up)
