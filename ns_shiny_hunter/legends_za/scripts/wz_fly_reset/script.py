import time
from enum import IntEnum

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames


class WildZoneFlyReset:
    class Mode(IntEnum):
        ROLL_TO_ENTER = 0
        WALK_TO_ENTER = 1
        INSTANT_ENTER = 2


    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerClient, resets: int = 0, mode: Mode = Mode.INSTANT_ENTER):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.resets = resets
        self.mode = mode

    def run(self):
        try:
            while True:
                self.resets += 1
                print(f"Reset #{self.resets}...")
                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    time.sleep(0.1)
                match self.mode:
                    case self.Mode.ROLL_TO_ENTER:
                        self.controller.click(Button.Y, post_delay=1.0)
                    case self.Mode.WALK_TO_ENTER:
                        self.controller.set_stick(ls_y=1, post_delay=0.5)
                        self.controller.click(Button.B, post_delay=0.5)
                        self.controller.clear()

                self.controller.click(Button.A)
                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    self.controller.click(Button.L)
                self.controller.click(Button.PLUS, post_delay=1.0)
                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A, post_delay=0.5)
        except KeyboardInterrupt:
            print(f"\nCompleted {self.resets} resets.")
            raise