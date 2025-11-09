import os.path
import pathlib
from dataclasses import dataclass
from enum import IntEnum, auto, Enum
from typing import Any, Final, Protocol

import cv2
import numpy as np

Frame = cv2.Mat | np.ndarray[Any, np.dtype] | np.ndarray


@dataclass
class BlurParams:
    ksize: tuple[int, int] = (5, 5)
    sigma_x: float = 0.0
    sigma_y: float = 0.0


@dataclass
class ThresholdParams:
    max_value: int = 255
    adaptive_method: int = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
    threshold_type: int = cv2.THRESH_BINARY
    block_size: int = 11
    c: float = 2


class RotationInvariantFrameProcessor:
    """Frame processor for detecting icons regardless of rotation within an ROI"""

    def __init__(self, x1: int, y1: int, x2: int, y2: int):
        self.x1: Final = x1
        self.y1: Final = y1
        self.x2: Final = x2
        self.y2: Final = y2

    def prepare_frame(self, frame: Frame) -> Frame:
        """Extract ROI from frame and convert to grayscale"""
        roi = frame[self.y1:self.y2, self.x1:self.x2]
        return cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)


class FrameProcessor(Protocol):
    def prepare_frame(self, frame: Frame) -> Frame:
        ...


class SimpleFrameProcessor(FrameProcessor):
    def __init__(self,
                 x: int,
                 y: int,
                 w: int,
                 h: int,
                 color_space: int | None = cv2.COLOR_BGR2GRAY,
                 blur_params: BlurParams | None = BlurParams(),
                 threshold_params: ThresholdParams | None = ThresholdParams()):
        self.x1: Final = x
        self.x2: Final = x + w
        self.y1: Final = y
        self.y2: Final = y + h
        self.color_space: Final = color_space
        self.blur_params: Final = blur_params
        self.threshold_params: Final = threshold_params

    @classmethod
    def from_points(cls, p1: tuple[int, int], p2: tuple[int, int], **kwargs) -> 'SimpleFrameProcessor':
        return cls(p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1], **kwargs)

    def prepare_frame(self, frame: Frame) -> Frame:
        frame = frame[self.y1:self.y2, self.x1:self.x2]
        if self.color_space is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.blur_params is not None:
            frame = cv2.GaussianBlur(frame, self.blur_params.ksize, sigmaX=self.blur_params.sigma_x, sigmaY=self.blur_params.sigma_y)
        if self.threshold_params is not None:
            frame = cv2.adaptiveThreshold(frame,
                                          self.threshold_params.max_value,
                                          self.threshold_params.adaptive_method,
                                          self.threshold_params.threshold_type,
                                          self.threshold_params.block_size,
                                          self.threshold_params.c)
        return frame


class PolygonFrameProcessor(FrameProcessor):
    def __init__(self,
                 points: np.ndarray,
                 ksize: tuple[int, int] = (5, 5),
                 sigma_x: int = 0):
        x, y, w, h = cv2.boundingRect(points)
        self.x1: Final = x
        self.x2: Final = x + w
        self.y1: Final = y
        self.y2: Final = y + h
        self.points: Final = points
        self.ksize: Final = ksize
        self.sigma_x: Final = sigma_x

    def prepare_frame(self, frame: Frame) -> Frame:
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [self.points], 255)
        frame = cv2.bitwise_and(frame, frame, mask=mask)
        frame = frame[self.y1:self.y2, self.x1:self.x2]
        return cv2.GaussianBlur(frame, self.ksize, self.sigma_x)


class ReferenceFrame:
    def matches(self, frame: Frame) -> bool:
        ...

    def get_percent_match(self, frame: Frame) -> float:
        ...


class SimpleReferenceFrame(ReferenceFrame):
    def __init__(self,
                 frame: Frame,
                 frame_processor: FrameProcessor,
                 threshold: int = 1):
        self.frame: Final = frame
        self.frame_processor: Final = frame_processor
        self.threshold: Final = threshold

    @classmethod
    def create_from_file(cls,
                         srcfile: str,
                         filepath: str,
                         frame_processor: FrameProcessor,
                         threshold: int = 1) -> ReferenceFrame:
        filepath = os.path.join(os.path.dirname(srcfile), 'frames', filepath)
        return cls.create_from_frame(cv2.imread(filepath), frame_processor, threshold)

    @classmethod
    def create_from_path(cls, filepath: pathlib.Path, frame_processor: FrameProcessor, threshold: int = 1):
        filepath = filepath.absolute()
        return cls.create_from_frame(cv2.imread(str(filepath)), frame_processor, threshold)

    @classmethod
    def create_from_frame(cls, frame: Frame, frame_processor: FrameProcessor,
                          threshold: int = 1) -> 'SimpleReferenceFrame':
        return cls(frame_processor.prepare_frame(frame), frame_processor, threshold)

    def matches(self, frame: Frame) -> bool:
        percent_match = self.get_percent_match(frame)
        return percent_match < self.threshold

    def get_percent_match(self, frame: Frame) -> float:
        frame = self.frame_processor.prepare_frame(frame)
        res = cv2.absdiff(self.frame, frame)
        res = res.astype(np.uint8)
        return (np.count_nonzero(res) * 100) / res.size


class CompositeReferenceFrame(ReferenceFrame):
    class Behavior(IntEnum):
        AND = auto()
        OR = auto()

    def __init__(self, behavior: Behavior, frames: tuple[ReferenceFrame, ...]):
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


class ReferenceFrameEnum(ReferenceFrame, Enum):
    def matches(self, frame: Frame) -> bool:
        return self.value.matches(frame)

    def get_percent_match(self, frame: Frame) -> float:
        return self.value.get_percent_match(frame)


class LoggingReferenceFrame(ReferenceFrame):
    def __init__(self, name: str, delegate: ReferenceFrame) -> None:
        super().__init__()
        self.name = name
        self.delegate = delegate

    def matches(self, frame: Frame) -> bool:
        self.get_percent_match(frame)
        matches = self.delegate.matches(frame)
        print(f"Matches for {self.name}: {matches}")
        return matches

    def get_percent_match(self, frame: Frame) -> float:
        percent_match = self.delegate.get_percent_match(frame)
        print(f"Percent match for {self.name}: {percent_match}")
        return percent_match
