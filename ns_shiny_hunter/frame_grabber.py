import sys
import threading
import time
from typing import Final

import cv2

from .frame import Frame


class FrameGrabber:
    def __init__(self,
                 source: int | str,
                 width: int = 1280,
                 height: int = 720,
                 fps: int = 60,
                 imshow: bool = True):
        self.source: Final = source
        self.width: Final = width
        self.height: Final = height
        self.fps: Final = fps
        self.imshow: Final = imshow

        self.video_capture: Final = self.create_video_capture(source)

        self.video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG'))
        self.video_capture.set(cv2.CAP_PROP_FPS, fps)
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self.video_capture_thread: Final = threading.Thread(target=self.run)
        self.running: threading.Event = threading.Event()

        self._frame_lock: Final = threading.Lock()
        self._frame: Frame | None = None

    @classmethod
    def create_video_capture(cls, source: int | str) -> cv2.VideoCapture:
        if sys.platform == 'win32':
           return cv2.VideoCapture(source, cv2.CAP_MSMF)
        return cv2.VideoCapture(source)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        if not self.running.is_set():
            self.running.set()
            self.video_capture_thread.start()

    def stop(self):
        self.running.clear()
        if self.video_capture_thread.is_alive():
            self.video_capture_thread.join()

    def run(self):
        try:
            while self.running.is_set():
                success, frame = self.video_capture.read()
                if not success:
                    continue
                if self.imshow:
                    cv2.imshow("Frame Grabber", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        self.running.clear()
                        break
                with self._frame_lock:
                    self._frame = frame
        finally:
            self.video_capture.release()

    @property
    def frame(self) -> Frame | None:
        with self._frame_lock:
            return self._frame

    def get_frame(self) -> Frame | None:
        """Thread-safe access to the most recent frame."""
        return self.frame

    def wait_for_frame(self, timeout: float = 5.0) -> Frame | None:
        """Block until a frame is available, or until timeout seconds elapse."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            f = self.frame
            if f is not None:
                return f
            time.sleep(0.016)
        return None
