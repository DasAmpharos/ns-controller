"""Base class for ns_shiny_hunter automation scripts."""

from __future__ import annotations

import time
from typing import Final

from loguru import logger

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame import ReferenceFrame
from ns_shiny_hunter.frame_grabber import FrameGrabber

_POLL_INTERVAL: Final = 1 / 30  # ~30 fps


class BaseScript:
    """Base class providing common frame-polling and controller utilities.

    Subclasses define their own ``__init__`` with any extra parameters they
    need, calling ``super().__init__(frame_grabber, controller)`` for the two
    shared fields, and implement ``run()`` for the automation loop.

    Example::

        class BenchReset(BaseScript):
            def __init__(self, frame_grabber, controller, resets=0):
                super().__init__(frame_grabber, controller)
                self.resets = resets

            def run(self):
                try:
                    while True:
                        self.resets += 1
                        logger.info(f"Reset #{self.resets}")
                        self.click_until(LegendsZAReferenceFrames.OVERWORLD, Button.A)
                except KeyboardInterrupt:
                    logger.info(f"Exiting after {self.resets} resets.")
    """

    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerClient) -> None:
        self.frame_grabber = frame_grabber
        self.controller = controller

    def run(self) -> None:
        raise NotImplementedError

    # ── Polling helpers ───────────────────────────────────────────────────────

    def wait_for(self, ref: ReferenceFrame, timeout: float = 30.0) -> bool:
        """Block until *ref* matches the current frame, polling at ~30 fps.

        Sends no controller inputs. Returns ``False`` if *timeout* elapses
        before a match is found.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = self.frame_grabber.get_frame()
            if frame is not None and ref.matches(frame):
                return True
            time.sleep(_POLL_INTERVAL)
        logger.warning("wait_for timed out after {}s", timeout)
        return False

    def wait_until_not(self, ref: ReferenceFrame, timeout: float = 30.0) -> bool:
        """Block until *ref* no longer matches the current frame.

        Returns ``False`` if *timeout* elapses without the state leaving.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = self.frame_grabber.get_frame()
            if frame is None or not ref.matches(frame):
                return True
            time.sleep(_POLL_INTERVAL)
        logger.warning("wait_until_not timed out after {}s", timeout)
        return False

    def click_until(
        self,
        ref: ReferenceFrame,
        *buttons: Button,
        post_delay: float = 0.1,
        timeout: float = 60.0,
    ) -> bool:
        """Click *buttons* repeatedly until *ref* matches the current frame.

        This replaces the common pattern::

            while not SomeState.matches(self.frame_grabber.frame):
                self.controller.click(Button.A)

        Returns ``False`` if *timeout* elapses without achieving the state.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            frame = self.frame_grabber.get_frame()
            if frame is not None and ref.matches(frame):
                return True
            self.controller.click(*buttons, post_delay=post_delay)
        logger.warning("click_until timed out after {}s", timeout)
        return False
