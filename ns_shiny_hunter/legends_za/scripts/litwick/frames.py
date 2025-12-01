import pathlib
from typing import Final

import cv2

from ns_shiny_hunter.frame import ReferenceFrameEnum, ReferenceFrames, FrameProcessors

FILE_PATH: Final = pathlib.Path(__file__)
FRAMES_DIR: Final = FILE_PATH.parent / "frames"

class LitwickScriptReferenceFrames(ReferenceFrameEnum):
    FRAME_0 = ReferenceFrames.template_from_path(
        threshold=0.5,
        # flags=cv2.IMREAD_GRAYSCALE,
        filepath=FRAMES_DIR / "frame-0.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_points((41, 41), (201, 201)),
            FrameProcessors.crop_circle(80, 80, 80),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    FRAME_1 = ReferenceFrames.template_from_path(
        threshold=0.5,
        # flags=cv2.IMREAD_GRAYSCALE,
        filepath=FRAMES_DIR / "frame-1.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_points((41, 41), (201, 201)),
            FrameProcessors.crop_circle(80, 80, 80),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    pass
# 41,41
# 201,201