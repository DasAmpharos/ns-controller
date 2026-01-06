import time
import traceback

import click

from ns_controller.client import NsControllerClient
from ns_controller.client_transport import NsControllerGrpcTransport, NsControllerNativeTransport, NsControllerTransport
from ns_controller.controller import Controller
from ns_controller.pb.ns_controller_pb2 import Button
from ns_controller.server import DEFAULT_HOST, DEFAULT_PORT
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.scripts.hyperspace.script import HyperspaceScript


@click.group()
def cli():
    pass


@cli.command()
@click.option("--host", default=DEFAULT_HOST, help="Server host")
@click.option("--port", default=DEFAULT_PORT, type=int, help="Server port")
@click.option("--source", type=int, default=0, help="Video source index")
@click.option("--imshow", help="Show video window")
@click.option("--resets", default=0, type=int)
def grpc(host: str, port: int, source: int, imshow: bool, resets: int) -> None:
    transport = NsControllerGrpcTransport(host, port)
    run(transport, source, imshow, resets)


@cli.command()
@click.option("--hid-path", default="/dev/hidg0")
@click.option("--source", type=int, default=0, help="Video source index")
@click.option("--imshow", help="Show video window")
@click.option("--resets", default=0, type=int)
def native(hid_path: str, source: int, imshow: bool, resets: int) -> None:
    controller = Controller()
    controller.connect(hid_path)
    transport = NsControllerNativeTransport(controller)
    time.sleep(1.0)

    run(transport, source, imshow, resets)


def run(transport: NsControllerTransport, source: int | str, imshow: bool, resets: int = 0) -> None:
    client = NsControllerClient(transport)
    try:
        with FrameGrabber(source, imshow=imshow) as frame_grabber:
            pair_controller(client)

            # BDSP
            # script = RamanasParkScript(
            #     controller=client,
            #     frame_grabber=frame_grabber,
            #     script_frames=ScriptFrames(
            #         location=LugiaReferenceFrames.LOCATION,
            #         pokemon_in_battle=LugiaReferenceFrames.POKEMON_IN_BATTLE,
            #         target_appeared=LugiaReferenceFrames.TARGET_APPEARED,
            #         target_dialog=LugiaReferenceFrames.TARGET_DIALOG,
            #     ),
            #     baseline=lugia.load_baseline(),
            #     software_errors=303,
            #     resets=resets
            # )

            # Legends ZA
            # script = FlyReset(FlyReset.WILD_ZONE_4, frame_grabber, client, resets=resets)
            # script = BenchReset(frame_grabber, client, resets=resets)
            # script = LitwickScript(frame_grabber, client, resets=resets)
            # script = SushiHighRoller(frame_grabber, client, state=State.ENTRANCE_1)
            # script = WildZoneFlyReset(frame_grabber, client, mode=WildZoneFlyReset.Mode.WALK_TO_ENTER, resets=resets)
            # script = SoftReset(frame_grabber, client, resets=resets)
            script = HyperspaceScript(frame_grabber, client, resets=resets)
            # script = DonutResetScript(frame_grabber, client, targets=['Water', 'All Types'], resets=resets)
            # script = TerrakionScript(client, resets)
            script.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        open_controller_menu(client)


def pair_controller(client: NsControllerClient):
    client.click(Button.L, Button.R, post_delay=0.75)
    client.click(Button.HOME, post_delay=3)
    client.click(Button.A, post_delay=3)


def open_controller_menu(client: NsControllerClient):
    client.clear()
    client.click(Button.HOME, post_delay=1.125)
    client.click(Button.DPAD_DOWN, post_delay=0.5)
    for _ in range(6):
        client.click(Button.DPAD_RIGHT, post_delay=0.05)
    client.click(Button.A, post_delay=1)
    client.click(Button.A)


if __name__ == "__main__":
    cli()
