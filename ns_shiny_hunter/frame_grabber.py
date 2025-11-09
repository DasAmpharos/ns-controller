import os
import threading
from collections import deque
from typing import Final

import cv2
from loguru import logger

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

        self.frame_buffer: Final = deque(maxlen=buffer_size)
        self.frame_buffer_lock: Final = threading.Lock()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        self.running.clear()
        self.video_capture_thread.start()

    def stop(self):
        self.running.set()
        self.video_capture_thread.join()
        self.video_capture.release()

    def run(self):
        frames = 0
        while not self.running.is_set():
            frame = self.read_frame()
            if frame is None:
                continue

            with self.frame_buffer_lock:
                self.frame_buffer.append(frame)

            if self.imshow:
                cv2.imshow('Frame Grabber', frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('s'):
                    filepath = os.path.join("frames", f'frame-{frames}.jpg')
                    filepath = os.path.abspath(filepath)
                    dirname = os.path.dirname(filepath)
                    os.makedirs(dirname, exist_ok=True)
                    cv2.imwrite(filepath, frame)
                    frames += 1
                elif key == ord('q'):
                    self.running.set()
                    break

    @property
    def frame(self) -> Frame | None:
        with self.frame_buffer_lock:
            return self.frame_buffer[-1] if self.frame_buffer else None

    @property
    def frames(self) -> list[Frame]:
        with self.frame_buffer_lock:
            return list(self.frame_buffer)

    def read_frame(self) -> Frame | None:
        success, frame = self.video_capture.read()
        if not success:
            logger.error('Failed to read frame')
            return None
        return frame
