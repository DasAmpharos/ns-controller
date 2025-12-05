import pathlib
from enum import IntEnum, auto, Enum
from typing import Any, Final, Protocol, override

import cv2
import numpy as np
from loguru import logger

Frame = cv2.Mat | np.ndarray[Any, np.dtype] | np.ndarray


class FrameProcessor(Protocol):
    def process_frame(self, frame: Frame) -> Frame:
        ...


class CompositeFrameProcessor(FrameProcessor):
    def __init__(self, *processors: FrameProcessor):
        self.m_processors: Final = processors

    @override
    def process_frame(self, frame: Frame) -> Frame:
        for processor in self.m_processors:
            frame = processor.process_frame(frame)
        return frame


class CropRect(FrameProcessor):
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x: Final = x
        self.y: Final = y
        self.w: Final = w
        self.h: Final = h

    @override
    def process_frame(self, frame: Frame) -> Frame:
        return frame[self.y:self.y + self.h, self.x:self.x + self.w]


class CropPoints(FrameProcessor):
    def __init__(self, p1: tuple[int, int], p2: tuple[int, int]):
        self.x1: Final = p1[0]
        self.y1: Final = p1[1]
        self.x2: Final = p2[0]
        self.y2: Final = p2[1]

    @override
    def process_frame(self, frame: Frame) -> Frame:
        return frame[self.y1:self.y2, self.x1:self.x2]


class CropCircle(FrameProcessor):
    def __init__(self, center_x: int, center_y: int, radius: int):
        self.center_x: Final = center_x
        self.center_y: Final = center_y
        self.radius: Final = radius

    @override
    def process_frame(self, frame: Frame) -> Frame:
        # Create a mask with the same dimensions as the frame
        mask = np.zeros(frame.shape[:2], np.uint8)
        # Draw a filled white circle on the mask
        cv2.circle(mask, (self.center_x, self.center_y), self.radius, 255, -1)
        # Apply the mask to the frame
        return cv2.bitwise_and(frame, frame, mask=mask)


class CropPolygon(FrameProcessor):
    def __init__(self, points: np.ndarray):
        self.points: Final = points
        self.bounds: Final = cv2.boundingRect(points)

    def process_frame(self, frame: Frame) -> Frame:
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [self.points], 255)
        frame = cv2.bitwise_and(frame, frame, mask=mask)
        x, y, w, h = self.bounds
        return frame[y:y + h, x:x + w]


class CvtColor(FrameProcessor):
    def __init__(self, code: int):
        self.m_code: Final = code

    def process_frame(self, frame: Frame) -> Frame:
        return cv2.cvtColor(frame, self.m_code)


class GaussianBlur(FrameProcessor):
    def __init__(self, ksize: tuple[int, int], sigma_x: float = 0.0, sigma_y: float = 0.0):
        self.ksize: Final = ksize
        self.sigma_x: Final = sigma_x
        self.sigma_y: Final = sigma_y

    def process_frame(self, frame: Frame) -> Frame:
        return cv2.GaussianBlur(frame, self.ksize, sigmaX=self.sigma_x, sigmaY=self.sigma_y)


class MedianBlur(FrameProcessor):
    def __init__(self, ksize: int = 5):
        self.ksize: Final = ksize

    def process_frame(self, frame: Frame) -> Frame:
        return cv2.medianBlur(frame, self.ksize)


class AdaptiveThreshold(FrameProcessor):
    def __init__(self,
                 max_value: int = 255,
                 adaptive_method: int = cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                 threshold_type: int = cv2.THRESH_BINARY,
                 block_size: int = 11,
                 c: float = 2):
        self.max_value: Final = max_value
        self.adaptive_method: Final = adaptive_method
        self.threshold_type: Final = threshold_type
        self.block_size: Final = block_size
        self.c: Final = c

    def process_frame(self, frame: Frame) -> Frame:
        return cv2.adaptiveThreshold(frame,
                                     self.max_value,
                                     self.adaptive_method,
                                     self.threshold_type,
                                     self.block_size,
                                     self.c)


class FrameProcessors:
    CVT_COLOR_BGR2GRAY: Final = CvtColor(cv2.COLOR_BGR2GRAY)
    GAUSSIAN_BLUR_DEFAULT: Final = GaussianBlur((3, 3), sigma_x=0.5, sigma_y=0.5)
    ADAPTIVE_THRESHOLD_DEFAULT: Final = AdaptiveThreshold()
    MEDIAN_BLUR_DEFAULT: Final = MedianBlur(5)

    @staticmethod
    def all(*processors: FrameProcessor) -> FrameProcessor:
        return CompositeFrameProcessor(*processors)

    @staticmethod
    def crop_rect(x: int,
                  y: int,
                  w: int,
                  h: int) -> FrameProcessor:
        return CropRect(x, y, w, h)

    @staticmethod
    def crop_points(p1: tuple[int, int],
                    p2: tuple[int, int]) -> FrameProcessor:
        return CropPoints(p1, p2)

    @staticmethod
    def crop_circle(center_x: int, center_y: int, radius: int) -> FrameProcessor:
        return CropCircle(center_x, center_y, radius)

    @staticmethod
    def crop_polygon(points: np.ndarray) -> FrameProcessor:
        return CropPolygon(points)

    @staticmethod
    def cvt_color(code: int) -> FrameProcessor:
        return CvtColor(code)

    @staticmethod
    def gaussian_blur(ksize: tuple[int, int],
                      sigma_x: float = 0.0,
                      sigma_y: float = 0.0) -> FrameProcessor:
        return GaussianBlur(ksize, sigma_x, sigma_y)

    @staticmethod
    def median_blur(ksize: int) -> FrameProcessor:
        return MedianBlur(ksize)

    @staticmethod
    def adaptive_threshold(max_value: int = 255,
                           adaptive_method: int = cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                           threshold_type: int = cv2.THRESH_BINARY,
                           block_size: int = 11,
                           c: float = 2) -> FrameProcessor:
        return AdaptiveThreshold(max_value, adaptive_method, threshold_type, block_size, c)


class ReferenceFrame:
    def matches(self, frame: Frame) -> bool:
        ...

    def get_percent_match(self, frame: Frame) -> float:
        ...


class ReferenceFrameTemplate(ReferenceFrame):
    def __init__(self, template: Frame, threshold: float, frame_processor: FrameProcessor, preprocessed: bool = True):
        self.preprocessed: Final = preprocessed
        if not preprocessed:
            template = frame_processor.process_frame(template)
        self.template: Final = template
        self.threshold: Final = threshold
        self.frame_processor: Final = frame_processor

    def matches(self, frame: Frame) -> bool:
        return self.get_percent_match(frame) > self.threshold

    def get_percent_match(self, frame: Frame) -> float:
        frame = self.frame_processor.process_frame(frame)
        res = cv2.absdiff(self.template, frame)
        res = res.astype(np.uint8)
        return 1 - np.count_nonzero(res) / res.size


class ReferenceFrameTemplateMatch(ReferenceFrame):
    def __init__(self, template: Frame, threshold: float, frame_processor: FrameProcessor,
                 method: int = cv2.TM_CCOEFF_NORMED,
                 preprocessed: bool = True):
        self.preprocessed: Final = preprocessed
        if not preprocessed:
            template = frame_processor.process_frame(template)
        self.template: Final = template
        self.threshold: Final = threshold
        self.frame_processor: Final = frame_processor
        self.method: Final = method

    def matches(self, frame: Frame) -> bool:
        return self.get_percent_match(frame) >= self.threshold

    def get_percent_match(self, frame: Frame) -> float:
        frame = self.frame_processor.process_frame(frame)
        result = cv2.matchTemplate(frame, self.template, self.method)
        min_val, max_val, _, _ = cv2.minMaxLoc(result)
        if self.method == cv2.TM_SQDIFF or self.method == cv2.TM_SQDIFF_NORMED:
            return 1.0 - min_val  # Invert for consistency
        return max_val


class CompositeReferenceFrame(ReferenceFrame):
    class Mode(IntEnum):
        AND = auto()
        OR = auto()

    def __init__(self, mode: Mode, *reference_frames: ReferenceFrame):
        self.mode: Final = mode
        self.reference_frames: Final = reference_frames

    def matches(self, frame: Frame) -> bool:
        match self.mode:
            case self.Mode.AND:
                return all(reference_frame.matches(frame) for reference_frame in self.reference_frames)
            case self.Mode.OR:
                return any(reference_frame.matches(frame) for reference_frame in self.reference_frames)

    def get_percent_match(self, frame: Frame) -> float:
        match self.mode:
            case self.Mode.AND:
                return sum(reference_frame.get_percent_match(frame) for reference_frame in self.reference_frames) / len(
                    self.reference_frames)
            case self.Mode.OR:
                return min(reference_frame.get_percent_match(frame) for reference_frame in self.reference_frames)


class LoggingReferenceFrame(ReferenceFrame):
    def __init__(self, name: str, delegate: ReferenceFrame, enabled: bool = True):
        self.name: Final = name
        self.delegate: Final = delegate
        self.enabled: Final = enabled

    def matches(self, frame: Frame) -> bool:
        self.get_percent_match(frame)
        matches = self.delegate.matches(frame)
        if self.enabled:
            logger.info(f"name={self.name}, matches={matches}")
        return matches

    def get_percent_match(self, frame: Frame) -> float:
        percent_match = self.delegate.get_percent_match(frame)
        if self.enabled:
            logger.info(f"name={self.name}, percent_match={percent_match}")
        return percent_match


class ReferenceFrames:
    @staticmethod
    def template_from_path(filepath: pathlib.Path, threshold: float, frame_processor: FrameProcessor,
                           flags: int = cv2.IMREAD_COLOR_BGR,
                           preprocessed: bool = True) -> ReferenceFrame:
        return ReferenceFrameTemplate(cv2.imread(str(filepath.absolute()), flags), threshold, frame_processor,
                                      preprocessed)

    @staticmethod
    def template_from_frame(frame: Frame, threshold: float, frame_processor: FrameProcessor,
                            preprocessed: bool = True) -> ReferenceFrame:
        return ReferenceFrameTemplate(frame, threshold, frame_processor, preprocessed)

    @staticmethod
    def template_match_from_path(filepath: pathlib.Path, threshold: float, frame_processor: FrameProcessor,
                                 flags: int = cv2.IMREAD_COLOR_BGR,
                                 method: int = cv2.TM_CCOEFF_NORMED,
                                 preprocessed: bool = True) -> ReferenceFrame:
        return ReferenceFrameTemplateMatch(cv2.imread(str(filepath.absolute()), flags), threshold, frame_processor,
                                           method, preprocessed)

    @staticmethod
    def template_match_from_frame(frame: Frame, threshold: float, frame_processor: FrameProcessor,
                                  method: int = cv2.TM_CCOEFF_NORMED,
                                  preprocessed: bool = True) -> ReferenceFrame:
        return ReferenceFrameTemplateMatch(frame, threshold, frame_processor, method, preprocessed)

    @staticmethod
    def composite(mode: CompositeReferenceFrame.Mode, *reference_frames: ReferenceFrame) -> ReferenceFrame:
        return CompositeReferenceFrame(mode, *reference_frames)

    @staticmethod
    def logging(name: str, delegate: ReferenceFrame, enabled: bool = True) -> ReferenceFrame:
        return LoggingReferenceFrame(name, delegate, enabled)


class ReferenceFrameEnum(ReferenceFrame, Enum):
    def matches(self, frame: Frame) -> bool:
        return self.value.matches(frame)

    def get_percent_match(self, frame: Frame) -> float:
        return self.value.get_percent_match(frame)
