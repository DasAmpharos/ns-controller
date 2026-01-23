import time

from loguru import logger

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button, Stick, Position


class VirizionScript:
    def __init__(self, controller: NsControllerClient, resets: int = 0):
        self.controller = controller
        self.total_resets = resets
        self.target_resets = 30

    def run(self):
        try:
            resets = 0
            delay = 4.0
            offset = 0.0
            while True:
                # Forward movement
                self.controller.set_stick(Stick.LS, Position(x=0.03, y=1.0))
                self.controller.click(Button.B)
                target_delay = delay + offset
                actual_delay = self.sleep(target_delay)
                offset = actual_delay - target_delay
                self.controller.clear()
                time.sleep(0.25)

                resets += 1
                self.total_resets += 1
                logger.info(f"Reset #{self.total_resets}...")
                if resets == self.target_resets:
                    logger.info(f"Completed {self.target_resets} resets.")
                    break

                # Backward movement
                self.controller.set_stick(Stick.LS, Position(x=-0.0165, y=-1.0))
                self.controller.click(Button.B)
                target_delay = delay + offset
                actual_delay = self.sleep(target_delay)
                offset = actual_delay - target_delay
                self.controller.clear()
                time.sleep(0.25)

                # self.controller.clear()

                # self.controller.set_state(
                #     controller_state=ControllerState(
                #         buttons=Button.Y,
                #         ls=Stick(y=-1.0)
                #     ),
                #     post_delay=0.1
                # )
                # self.controller.clear(post_delay=1.2)

                # self.controller.set_stick(ls_y=-1.0, post_delay=0.1)
                # self.controller.set_stick(ls_y=0.0, post_delay=0.1)
                # self.controller.click(Button.Y, post_delay=1.3)
        except KeyboardInterrupt:
            print("\nScript terminated by user.")
            raise

    @staticmethod
    def sleep(seconds: float) -> float:
        start = time.perf_counter()
        time.sleep(seconds)
        end = time.perf_counter()
        return end - start
