import queue
import threading
from typing import Final

import cv2
from loguru import logger

from .frame import Frame


class FrameGrabber:
    def __init__(self,
                 source: int | str,
                 width: int = 1280,
                 height: int = 720,
                 fps: int = 60):
        self.source: Final = source
        self.width: Final = width
        self.height: Final = height
        self.fps: Final = fps

        self.video_capture: Final = cv2.VideoCapture(source)
        self.video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG'))
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.video_capture.set(cv2.CAP_PROP_FPS, fps)

        self.video_capture_thread: Final = threading.Thread(target=self.run)
        self.running: threading.Event = threading.Event()

        # Queue for "processing" (sequential, blocking access)
        # Use a small maxsize so we don't store thousands of frames if processing is slow
        self.frame_queue: Final = queue.Queue(maxsize=60)

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

    def clear_queue(self):
        """Discards all pending frames in the processing queue."""
        with self.frame_queue.mutex:
            self.frame_queue.queue.clear()

    def read_next(self, timeout: float = 1.0) -> Frame | None:
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def run(self):
        while not self.running.is_set():
            success, frame = self.video_capture.read()
            if not success:
                continue

            # Update processing queue
            # If queue is full, remove oldest item to make room (drop frame)
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put(frame)
