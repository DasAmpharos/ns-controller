from ns_controller.client import NsControllerGrpcClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames.frames import LegendsZAReferenceFrames


class BenchReset:
    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerGrpcClient, resets: int = 0):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.resets = resets

    def run(self):
        try:
            while True:
                self.resets += 1
                print(f"Reset #{self.resets}...")
                self.controller.set_stick(ls_y=-1, post_delay=0.2)
                self.controller.clear()

                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)
        except KeyboardInterrupt:
            print(f"\nExiting BenchReset after {self.resets} resets...")
