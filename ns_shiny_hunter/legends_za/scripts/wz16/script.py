import time

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames
from ns_shiny_hunter.legends_za.scripts.wz16.frames import WildZone16ReferenceFrames


class WildZone16:
    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerClient, resets: int = 1):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.resets = resets

    def run(self):
        try:
            while True:
                print(f"Reset #{self.resets}...")
                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    time.sleep(0.1)

                self.controller.set_stick(ls_y=1, post_delay=0.3)
                self.controller.click(Button.B)

                while not WildZone16ReferenceFrames.PRESS_A_TO_ENTER.matches(self.frame_grabber.frame):
                    time.sleep(0.1)
                self.controller.clear()

                self.controller.click(Button.A)

                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    self.controller.click(Button.L)

                self.controller.click(Button.PLUS)

                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)

                self.resets += 1
        except KeyboardInterrupt:
            print(f"\nCompleted {self.resets} resets.")
            raise