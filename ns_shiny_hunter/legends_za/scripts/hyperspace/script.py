from ns_controller.client import NsControllerGrpcClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.scripts.hyperspace.frames import HyperspaceReferenceFrames


class HyperspaceScript:
    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerGrpcClient, resets: int = 0):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.resets = resets

    def run(self):
        try:
            while True:
                self.resets += 1
                print(f"Reset #{self.resets}...")
                while not HyperspaceReferenceFrames.MAP.matches(self.frame_grabber.frame):
                    self.controller.click(Button.PLUS, post_delay=0.15)
                    if HyperspaceReferenceFrames.PROMPT_TO_LEAVE.matches(self.frame_grabber.frame):
                        self.controller.click(Button.B)
                while HyperspaceReferenceFrames.MAP.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)
                    if HyperspaceReferenceFrames.SPOTTED.matches(self.frame_grabber.frame):
                        print("Spotted, exiting script for manual control...")
                        break
        except KeyboardInterrupt:
            print(f"\nCompleted {self.resets} resets.")
            raise
