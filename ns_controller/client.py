import time

import httpx

from ns_controller.controller import ControllerInput, Button, DPadButton


class NsControllerClient:
    def __init__(self, host: str, port: int, scheme: str = "http") -> None:
        self.client = httpx.Client(base_url=f"{scheme}://{host}:{port}", timeout=None)

    def press_buttons(self, buttons: list[Button]) -> None:
        self.client.post("/buttons/press", json=buttons)

    def release_buttons(self, buttons: list[Button]) -> None:
        self.client.post("/buttons/release", json=buttons)

    def press_dpad(self, buttons: list[DPadButton]) -> None:
        self.client.post("/dpad/press", json=buttons)

    def release_dpad(self, buttons: list[DPadButton]) -> None:
        self.client.post("/dpad/release", json=buttons)


    def clear(self, up: float | None = 0.1):
        self.client.post("/clear")
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
