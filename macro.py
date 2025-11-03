import signal
import time
from datetime import datetime, timedelta

import click

from ns_controller.client import NsControllerClient
from ns_controller.controller import ControllerInput


@click.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=8000, type=int, help="Server port")
def main(host: str, port: int) -> None:
    client = NsControllerClient(host, port)
    try:
        pair_controller(client)
        wz_20_alphas(client)
        # wz_20_runaround(client)
        # wz_13(client, resets=75)
        # bench_reset(client, total_time=timedelta(hours=8))
        # wz_2(client, resets=300)
        # wz_16(client, resets=301)
    finally:
        open_controller_menu(client)


def pair_controller(client: NsControllerClient):
    client.send_input(ControllerInput(buttons=ControllerInput.Buttons(l=True, r=True)), down=0.5)
    client.send_input(ControllerInput(buttons=ControllerInput.Buttons(home=True)), down=0.1, up=3)
    client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), down=0.1, up=3)


def open_controller_menu(client: NsControllerClient):
    client.send_input(ControllerInput())
    client.send_input(ControllerInput(buttons=ControllerInput.Buttons(home=True)), down=0.1, up=1)
    client.send_input(ControllerInput(dpad=ControllerInput.DPad(down=True)), down=0.1, up=0.5)
    for _ in range(6):
        client.send_input(ControllerInput(dpad=ControllerInput.DPad(right=True)), down=0.1, up=0.1)
    client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), down=0.1, up=1)
    client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), down=0.1)


def wz_2(client: NsControllerClient, resets: int = 0):
    try:
        while True:
            resets += 1
            print(f"Reset #{resets}...")
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), down=0.1, up=2.25)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(plus=True)), down=0.1, up=1.25)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), down=0.1, up=0.75)
            client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), down=0.1, up=3.25)
    except KeyboardInterrupt:
        print(f"\nCompleted {resets} resets.")
        raise


def wz_16(client: NsControllerClient, resets: int = 0):
    try:
        while True:
            resets += 1
            print(f"Reset #{resets}...")
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(b=True),
                    sticks=ControllerInput.Sticks(
                        ls=ControllerInput.Sticks.Axis(x=0, y=1)
                    )
                ),
                down=1.0,
                up=0.1
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(a=True)
                ),
                down=0.1,
                up=2.5
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(b=True),
                    sticks=ControllerInput.Sticks(
                        ls=ControllerInput.Sticks.Axis(x=0.05, y=1)
                    )
                ),
                down=10,
                up=0.1
            )
            # client.send_input(ControllerInput(buttons=ControllerInput.Buttons(y=True)))
            # time.sleep(1.5)
            # client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)))
            # time.sleep(2.25)
            # client.send_input(ControllerInput(buttons=ControllerInput.Buttons(plus=True)))
            # time.sleep(1.25)
            # client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)))
            # time.sleep(0.75)
            # client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)))
            # time.sleep(3.25)
    except KeyboardInterrupt:
        print(f"\nCompleted {resets} resets.")
        raise


def wz_13(client: NsControllerClient, resets: int = 0):
    # frame_grabber = FrameGrabber(0)
    try:
        while True:
            resets += 1
            print(f"Reset #{resets}...")
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(b=True),
                    sticks=ControllerInput.Sticks(
                        ls=ControllerInput.Sticks.Axis(x=0, y=1)
                    )
                ),
                down=1.0,
                up=0.1
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(a=True)
                ),
                down=0.1,
                up=1.5
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(b=True),
                    sticks=ControllerInput.Sticks(
                        ls=ControllerInput.Sticks.Axis(x=-0.075, y=1)
                    )
                ),
                down=11.5,
                up=0.1
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(a=True)
                ),
                down=0.1,
                up=2.5
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(plus=True)
                ),
                down=0.1,
                up=0.1
            )
            client.send_input(
                controller_input=ControllerInput(
                    sticks=ControllerInput.Sticks(
                        ls=ControllerInput.Sticks.Axis(
                            x=0.5,
                            y=0.1
                        )
                    )
                ),
                down=0.1,
                up=0.1
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(a=True)
                ),
                down=0.1,
                up=0.75
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(a=True)
                ),
                down=0.1,
                up=3.25
            )
    except KeyboardInterrupt:
        print(f"\nCompleted {resets} resets.")
        raise


def wz_20_runaround(client: NsControllerClient):
    try:
        client.send_input(ControllerInput(buttons=ControllerInput.Buttons(y=True)), down=0.1, up=1.5)
        client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), down=0.1, up=2.5)
        # client.send_input(ControllerInput(sticks=ControllerInput.Sticks(ls=ControllerInput.Sticks.Axis(x=1))), down=0.1, up=0.1)
        # client.send_input(ControllerInput(buttons=ControllerInput.Buttons(l=True)), down=0.1, up=0.1)
        client.send_input(
            controller_input=ControllerInput(
                buttons=ControllerInput.Buttons(b=True),
                sticks=ControllerInput.Sticks(
                    ls=ControllerInput.Sticks.Axis(x=1, y=0),
                    rs=ControllerInput.Sticks.Axis(x=-0.1736, y=0)
                )
            )
        )
        signal.pause()
    except KeyboardInterrupt:
        print("\nStopped runaround.")
        raise


def wz_20_alphas(client: NsControllerClient, resets: int = 0):
    try:
        while True:
            resets += 1
            client.ls.update(x=0.1, y=1)
            client.buttons.b.click()


            client.send_input(
                controller_input=ControllerInput(
                    sticks=ControllerInput.Sticks(
                        ls=ControllerInput.Sticks.Axis(x=0.1, y=1),
                    )
                )
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(b=True)
                ),
                down=0.1
            )
            time.sleep(2.3)
            client.clear()

            client.send_input(
                controller_input=ControllerInput(
                    sticks=ControllerInput.Sticks(
                        ls=ControllerInput.Sticks.Axis(x=-0.1, y=-1),
                    )
                )
            )
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(b=True)
                ),
                down=0.1
            )
            time.sleep(2.5)
            client.clear()

            start = time.time()
            while time.time() - start < 5.0:
                client.send_input(
                    controller_input=ControllerInput(
                        buttons=ControllerInput.Buttons(a=True),
                    ),
                    down=0.1
                )
            time.sleep(12)
    except KeyboardInterrupt:
        print(f"\nCompleted {resets} resets.")


def bench_reset(client: NsControllerClient, total_time: timedelta = timedelta(hours=1, minutes=30)):
    start = datetime.now()
    try:
        # hold down left stick
        client.send_input(ControllerInput(sticks=ControllerInput.Sticks(ls=ControllerInput.Sticks.Axis(y=-1))))
        while datetime.now() - start < total_time:
            client.send_input(
                controller_input=ControllerInput(
                    buttons=ControllerInput.Buttons(a=True),
                    sticks=ControllerInput.Sticks(ls=ControllerInput.Sticks.Axis(y=-1))
                ),
                down=0.1,
                up=0.1
            )
        # go to sleep
        client.send_input(ControllerInput(buttons=ControllerInput.Buttons(home=True)), down=1.5, up=0.1)
        client.send_input(ControllerInput(buttons=ControllerInput.Buttons(a=True)), down=0.1, up=0.1)
    except KeyboardInterrupt:
        elapsed = datetime.now() - start
        print(f"\nElapsed time: {elapsed}.")


if __name__ == "__main__":
    main()
