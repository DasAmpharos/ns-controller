import time

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame_grabber import FrameGrabber


class LitwickScript:
    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerClient, resets: int = 0):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.resets = resets

    def run(self):
        try:
            while True:
                delay = 5.5
                self.resets += 1
                print(f"Reset #{self.resets}...")
                self.controller.set_stick(ls_x=0.01, ls_y=1)
                if self.resets == 1:
                    self.controller.click(Button.B, down=0.5)
                    delay -= 0.5
                time.sleep(delay)
                self.controller.set_stick(ls_x=0.01, ls_y=-1)
                time.sleep(5.5)
                # self.controller.click(Button.B, down=0.5, post_delay=6.0)
        except KeyboardInterrupt:
            print(f"\nCompleted {self.resets} resets.")
            raise