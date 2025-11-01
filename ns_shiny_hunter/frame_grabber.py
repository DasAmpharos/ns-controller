import threading
from collections import deque
from typing import Final

import cv2
from loguru import logger

from .atomic import AtomicValue
from .frame import Frame


class FrameGrabber:
    def __init__(self,
                 source: int | str,
                 width: int = 1280,
                 height: int = 720,
                 fps: int = 30,
                 imshow: bool = True):
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
        self.running: Final = AtomicValue(False)

        self.frame: Final = AtomicValue(self.read_frame())
        self.frame_buffer_lock: Final = threading.Lock()
        self.frame_buffer = deque(maxlen=fps * 15)

    def start(self):
        if self.running.compare_and_set(False, True):
            self.video_capture_thread.start()

    def stop(self):
        if self.running.compare_and_set(True, False):
            self.video_capture_thread.join()
            self.video_capture.release()

    def dump_buffer(self, output_path: str):
        with self.frame_buffer_lock:
            frame_buffer = self.frame_buffer
            self.frame_buffer = deque(maxlen=self.fps * 15)

        fourcc = cv2.VideoWriter.fourcc(*'X264')
        video_writer = cv2.VideoWriter(output_path, fourcc, self.fps, (self.width, self.height))
        while len(frame_buffer) > 0:
            frame = frame_buffer.popleft()
            video_writer.write(frame)
        video_writer.release()
        logger.info(f'Dumped frame buffer to {output_path}')

    def run(self):
        while self.running.get():
            frame = self.read_frame()
            if frame is not None:
                self.frame.set(frame)
            if self.imshow:
                cv2.imshow('Frame Grabber', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running.set(False)
                    break
            with self.frame_buffer_lock:
                if len(self.frame_buffer) == self.frame_buffer.maxlen:
                    self.frame_buffer.popleft()
                self.frame_buffer.append(frame)

    def read_frame(self) -> Frame:
        success, frame = self.video_capture.read()
        if not success:
            logger.error('Failed to read frame')
            return None
        return frame
