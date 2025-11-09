import click

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import ControllerState, Button
from ns_controller.server import DEFAULT_HOST, DEFAULT_PORT
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.scripts.sushi_high_roller.script import SushiHighRoller, State


@click.command()
@click.option("--host", default=DEFAULT_HOST, help="Server host")
@click.option("--port", default=DEFAULT_PORT, type=int, help="Server port")
@click.option("--resets", default=1, type=int)
def main(host: str, port: int, resets: int) -> None:
    client = NsControllerClient(host, port)
    try:
        with FrameGrabber(0) as frame_grabber:
            pair_controller(client)
            script = SushiHighRoller(frame_grabber, client, state=State.OVERWORLD_POKEMON_CENTER)
            script.run()
    finally:
        open_controller_menu(client)


def pair_controller(client: NsControllerClient):
    client.click(Button.L, Button.R, post_delay=0.5)
    client.click(Button.HOME, post_delay=3)
    client.click(Button.A, post_delay=3)


def open_controller_menu(client: NsControllerClient):
    client.clear()
    client.click(Button.HOME, post_delay=1)
    client.click(Button.DPAD_DOWN, post_delay=0.5)
    for _ in range(6):
        client.click(Button.DPAD_RIGHT, post_delay=0.05)
    client.click(Button.A, post_delay=1)
    client.click(Button.A)


# def wz_2(client: NsControllerClient, resets: int = 0):
#     try:
#         while True:
#             resets += 1
#             print(f"Reset #{resets}...")
#             client.send_input(make_state(buttons=[Button.A]), down=0.1, up=2.25)
#             client.send_input(make_state(buttons=[Button.PLUS]), down=0.1, up=1.25)
#             client.send_input(make_state(buttons=[Button.A]), down=0.1, up=0.75)
#             client.send_input(make_state(buttons=[Button.A]), down=0.1, up=3.25)
#     except KeyboardInterrupt:
#         print(f"\nCompleted {resets} resets.")
#         raise
#
#
# def wz_16(client: NsControllerClient, resets: int = 0):
#     try:
#         while True:
#             resets += 1
#             print(f"Reset #{resets}...")
#             client.send_input(
#                 make_state(buttons=[Button.B], ls_x=0, ls_y=1),
#                 down=1.0,
#                 up=0.1
#             )
#             client.send_input(
#                 make_state(buttons=[Button.A]),
#                 down=0.1,
#                 up=2.5
#             )
#             client.send_input(
#                 make_state(buttons=[Button.B], ls_x=0.05, ls_y=1),
#                 down=10,
#                 up=0.1
#             )
#     except KeyboardInterrupt:
#         print(f"\nCompleted {resets} resets.")
#         raise
#
#
# def wz_13(client: NsControllerClient, resets: int = 0):
#     # frame_grabber = FrameGrabber(0)
#     try:
#         while True:
#             resets += 1
#             print(f"Reset #{resets}...")
#             client.send_input(
#                 make_state(buttons=[Button.B], ls_x=0, ls_y=1),
#                 down=1.0,
#                 up=0.1
#             )
#             client.send_input(
#                 make_state(buttons=[Button.A]),
#                 down=0.1,
#                 up=1.5
#             )
#             client.send_input(
#                 make_state(buttons=[Button.B], ls_x=-0.075, ls_y=1),
#                 down=11.5,
#                 up=0.1
#             )
#             client.send_input(
#                 make_state(buttons=[Button.A]),
#                 down=0.1,
#                 up=2.5
#             )
#             client.send_input(
#                 make_state(buttons=[Button.PLUS]),
#                 down=0.1,
#                 up=0.1
#             )
#             client.send_input(
#                 make_state(ls_x=0.5, ls_y=0.1),
#                 down=0.1,
#                 up=0.1
#             )
#             client.send_input(
#                 make_state(buttons=[Button.A]),
#                 down=0.1,
#                 up=0.75
#             )
#             client.send_input(
#                 make_state(buttons=[Button.A]),
#                 down=0.1,
#                 up=3.25
#             )
#     except KeyboardInterrupt:
#         print(f"\nCompleted {resets} resets.")
#         raise
#
#
# def wz_20_runaround(client: NsControllerClient):
#     try:
#         client.send_input(make_state(buttons=[Button.Y]), down=0.1, up=1.5)
#         client.send_input(make_state(buttons=[Button.A]), down=0.1, up=2.5)
#         client.send_input(
#             make_state(buttons=[Button.B], ls_x=1, ls_y=0, rs_x=-0.1736, rs_y=0)
#         )
#         signal.pause()
#     except KeyboardInterrupt:
#         print("\nStopped runaround.")
#         raise

#
# def wz_20_alphas(client: NsControllerClient, resets: int = 0):
#     try:
#         while True:
#             resets += 1
#             # run forward and stop
#             client.set_stick(ls_y=1, post_delay=0.5)
#             client.click([Button.B], down=0.5, post_delay=0.1)
#             time.sleep(1.8)
#             client.clear(0.1)
#             # run backward and stop
#             client.set_stick(ls_y=-1, post_delay=0.5)
#             client.click([Button.B], down=0.5, post_delay=0.1)
#             time.sleep(2.2)
#             # spam A
#             start = time.time()
#             while time.time() - start < 5.0:
#                 client.click([Button.A], down=0.1, post_delay=0.05)
#             client.clear(0.1)
#             time.sleep(12.5)
#     except KeyboardInterrupt:
#         print(f"\nCompleted {resets} resets.")


# def bench_reset(client: NsControllerClient, total_time: timedelta | None = None):
#     start = datetime.now()
#     try:
#         # hold down left stick
#         client.set_stick(ls_y=-1, post_delay=0.1)
#         while not total_time or datetime.now() - start < total_time:
#             client.click([Button.A], down=0.1, post_delay=0.1)
#         if total_time and datetime.now() - start >= total_time:
#             client.click([Button.HOME], down=1.5, post_delay=0.1)
#             client.click([Button.A], down=0.1, post_delay=0.1)
#             exit(0)
#     except KeyboardInterrupt:
#         elapsed = datetime.now() - start
#         print(f"\nElapsed time: {elapsed}.")


if __name__ == "__main__":
    main()
