import os.path
from abc import abstractmethod
from enum import IntEnum, auto, Enum
from typing import Any, Final

import cv2
import numpy as np

Frame = cv2.Mat | np.ndarray[Any, np.dtype] | np.ndarray


class FrameProcessor:
    def __init__(self,
                 x: int,
                 y: int,
                 w: int,
                 h: int,
                 ksize=(5, 5),
                 sigma_x=0,
                 max_value=255,
                 block_size=99,
                 c=3):
        self.x1: Final = x
        self.x2: Final = x + w
        self.y1: Final = y
        self.y2: Final = y + h
        self.ksize: Final = ksize
        self.sigma_x: Final = sigma_x
        self.max_value: Final = max_value
        self.block_size: Final = block_size
        self.c: Final = c

    def prepare_frame(self, frame: Frame) -> Frame:
        frame = frame[self.y1:self.y2, self.x1:self.x2]
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame = cv2.GaussianBlur(frame, self.ksize, self.sigma_x)
        return cv2.adaptiveThreshold(frame,
                                     self.max_value,
                                     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY,
                                     self.block_size,
                                     self.c)


class ReferenceFrame:
    @classmethod
    def create_from_file(cls, srcfile: str, filepath: str, frame_processor: FrameProcessor, threshold: int = 1):
        return ReferenceFrameFactory.create_from_file(srcfile, filepath, frame_processor, threshold)

    @classmethod
    def create_from_frame(cls, frame: Frame, frame_processor: FrameProcessor, threshold: int = 1):
        return ReferenceFrameFactory.create_from_frame(frame, frame_processor, threshold)

    @abstractmethod
    def matches(self, frame: Frame) -> bool:
        ...

    @abstractmethod
    def get_percent_match(self, frame: Frame) -> float:
        ...


class ReferenceFrameEnum(ReferenceFrame, Enum):
    def matches(self, frame: Frame) -> bool:
        return self.value.matches(frame)

    def get_percent_match(self, frame: Frame) -> float:
        return self.value.get_percent_match(frame)


class CompositeReferenceFrame(ReferenceFrame):
    class Behavior(IntEnum):
        AND = auto()
        OR = auto()

    def __init__(self, behavior: Behavior, frames: list[ReferenceFrame]):
        self.behavior: Final = behavior
        self.frames: Final = frames

    def matches(self, frame: Frame) -> bool:
        match self.behavior:
            case CompositeReferenceFrame.Behavior.AND:
                return all(ref.matches(frame) for ref in self.frames)
            case CompositeReferenceFrame.Behavior.OR:
                return any(ref.matches(frame) for ref in self.frames)
            case _:
                return False

    def get_percent_match(self, frame: Frame) -> float:
        match self.behavior:
            case CompositeReferenceFrame.Behavior.AND:
                return sum(ref.get_percent_match(ref) for ref in self.frames) / len(self.frames)
            case CompositeReferenceFrame.Behavior.OR:
                return min(ref.get_percent_match(frame) for ref in self.frames)
            case _:
                return 100.0


class ReferenceFrameFactory:
    class _ReferenceFrame(ReferenceFrame):
        def __init__(self,
                     frame: Frame,
                     frame_processor: FrameProcessor,
                     threshold: int = 1):
            self.frame: Final = frame
            self.frame_processor: Final = frame_processor
            self.threshold: Final = threshold

        def matches(self, frame: Frame) -> bool:
            return self.get_percent_match(frame) < self.threshold

        def get_percent_match(self, frame: Frame) -> float:
            frame = self.frame_processor.prepare_frame(frame)
            res = cv2.absdiff(self.frame, frame)
            res = res.astype(np.uint8)
            return (np.count_nonzero(res) * 100) / res.size

    @classmethod
    def create_from_file(cls,
                         srcfile: str,
                         filepath: str,
                         frame_processor: FrameProcessor,
                         threshold: int = 1) -> ReferenceFrame:
        filepath = os.path.join(os.path.dirname(srcfile), 'frames', filepath)
        return cls.create_from_frame(cv2.imread(filepath), frame_processor, threshold)

    @staticmethod
    def create_from_frame(frame: Frame, frame_processor: FrameProcessor, threshold: int = 1) -> ReferenceFrame:
        return ReferenceFrameFactory._ReferenceFrame(frame_processor.prepare_frame(frame), frame_processor, threshold)