import time

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button, ControllerState, Stick


class TerrakionScript:
    def __init__(self, controller: NsControllerClient, resets: int = 0):
        self.controller = controller
        self.total_resets = resets
        self.target_resets = 110

    def run(self):
        try:
            resets = 0
            while True:
                resets += 1
                self.total_resets += 1
                print(f"Reset #{self.total_resets}...")
                self.controller.click(Button.A, post_delay=2.9)
                self.controller.click(Button.Y, post_delay=1.05)

                self.controller.set_stick(ls_y=-1.0, post_delay=None)
                self.controller.click(Button.Y)
                self.controller.clear()
                time.sleep(1.05)
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

                self.controller.click(Button.A, post_delay=2.9)
                if resets == self.target_resets:
                    print(f"Completed {self.target_resets} resets.")
                    break
        except KeyboardInterrupt:
            print("\nScript terminated by user.")
            raise
