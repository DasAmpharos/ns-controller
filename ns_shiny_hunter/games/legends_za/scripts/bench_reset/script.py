from loguru import logger

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.base_script import BaseScript
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames


class BenchReset(BaseScript):
    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerClient, resets: int = 0):
        super().__init__(frame_grabber, controller)
        self.resets = resets

    def run(self) -> None:
        try:
            while True:
                self.resets += 1
                logger.info("Reset #{}...", self.resets)
                self.controller.set_stick(ls_y=-1, post_delay=0.2)
                self.controller.clear()
                self.click_until(LegendsZAReferenceFrames.OVERWORLD, Button.A)
        except KeyboardInterrupt:
            logger.info("Exiting BenchReset after {} resets.", self.resets)

