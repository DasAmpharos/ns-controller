from contextlib import contextmanager
from typing import Final

from ns_controller.client import NsControllerClient
from .atomic import AtomicValue
from .frame_grabber import FrameGrabber


class Bot:
    def __init__(self,
                 controller: NsControllerClient,
                 frame_grabber: FrameGrabber):
        self.controller: Final = controller
        self.frame_grabber: Final = frame_grabber
        self.is_running = AtomicValue(False)

    @classmethod
    @contextmanager
    def create(cls, controller: NsControllerClient, frame_grabber: FrameGrabber):
        bot = cls(controller, frame_grabber)
        try:
            bot.start()
            yield bot
        finally:
            bot.stop()

    def start(self):
        self.frame_grabber.start()
        self.is_running.compare_and_set(False, True)

    def stop(self):
        self.is_running.compare_and_set(True, False)
        self.frame_grabber.stop()
