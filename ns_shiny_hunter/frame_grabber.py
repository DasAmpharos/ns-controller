import threading
from typing import Final

import cv2

from .frame import Frame


class FrameGrabber:
    def __init__(self,
                 source: int | str,
                 width: int = 1280,
                 height: int = 720,
                 fps: int = 60,
                 imshow: bool = True,
                 buffer_size: int = 30):
        self.source: Final = source
        self.width: Final = width
        self.height: Final = height
        self.fps: Final = fps
        self.imshow: Final = imshow

        self.video_capture: Final = cv2.VideoCapture(source)
        self.video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG'))
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.video_capture.set(cv2.CAP_PROP_FPS, fps)

        self.video_capture_thread: Final = threading.Thread(target=self.run)
        self.running: threading.Event = threading.Event()

        self._frame_lock: Final = threading.Lock()
        self._frame: Frame | None = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        if not self.running.is_set():
            self.running.clear()
            self.video_capture_thread.start()

    def stop(self):
        self.running.clear()
        if self.video_capture_thread.is_alive():
            self.video_capture_thread.join()
        self.video_capture.release()

    def run(self):
        while not self.running.is_set():
            success, frame = self.video_capture.read()
            if not success:
                continue
            with self._frame_lock:
                self._frame = frame

    @property
    def frame(self) -> Frame | None:
        with self._frame_lock:
            return self._frame
