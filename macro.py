import time

import click

from ns_controller.client import NsControllerClient
from ns_controller.controller import ControllerInput


@click.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=8000, type=int, help="Server port")
def main(host: str, port: int) -> None:
    client = NsControllerClient(host, port)
    bench_reset(client, resets=20)


def wz_2(client: NsControllerClient, resets: int = 0):
    try:
        while True:
            resets += 1
            print(f"Reset #{resets}...")
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), up=2.25)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(plus=True)), up=1.25)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), up=0.75)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), up=3.25)
    except KeyboardInterrupt:
        print(f"\nCompleted {resets} resets.")


def wz_16(client: NsControllerClient, resets: int = 0):
    try:
        while True:
            resets += 1
            print(f"Reset #{resets}...")
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(y=True)), up=1.5)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), up=2.25)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(plus=True)), up=1.25)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), up=0.75)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), up=3.25)
    except KeyboardInterrupt:
        print(f"\nCompleted {resets} resets.")


def bench_reset(client: NsControllerClient, resets: int = 0):
    try:
        while resets < 500:
            resets += 1
            print(f"Reset #{resets}...")

            client.send_input(ControllerInput(sticks=ControllerInput.Sticks(ls=ControllerInput.Sticks.Axis(y=-1))), up=0.5)

            # spam A button for 20 seconds
            start = time.time()
            while time.time() - start < 20:
                client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)))
        # go to sleep
        client.send_input(ControllerInput(buttons=ControllerInput.Buttons(home=True)), down=1.5, up=0.5)
        client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)))
    except KeyboardInterrupt:
        print(f"\nCompleted {resets} resets.")


if __name__ == "__main__":
    main()
