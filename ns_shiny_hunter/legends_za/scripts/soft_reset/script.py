from InquirerPy import inquirer
from loguru import logger

from ns_controller.client import NsControllerGrpcClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames


class SoftReset:
    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerGrpcClient, resets: int = 0):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.resets = resets

    def run(self):
        try:
            while True:
                self.resets += 1
                logger.info(f"Reset #{self.resets}...")
                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)

                prompt = inquirer.confirm(message='Is this a shiny?')
                if prompt.execute():
                    break
                self.controller.click(Button.HOME, post_delay=1.2)
                self.controller.click(Button.X)
        except KeyboardInterrupt:
            print(f"\nExiting script after {self.resets} resets...")
