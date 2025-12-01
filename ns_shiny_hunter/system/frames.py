import pathlib
from typing import Final

from ns_shiny_hunter.frame import ReferenceFrameEnum, ReferenceFrames, FrameProcessors

FILEPATH: Final = pathlib.Path(__file__)
FRAMES_DIR: Final = FILEPATH.parent / "frames"


class SystemReferenceFrames(ReferenceFrameEnum):
    SW1_CHANGE_GRIP_ORDER = ReferenceFrames.template_from_path(
        threshold=0.05,
        filepath=FRAMES_DIR / "sw1-change-grip-order.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(x=463, y=587, w=354, h=21),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
