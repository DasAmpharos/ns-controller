import pathlib
from typing import Final

from ns_shiny_hunter.frame import ReferenceFrameEnum, ReferenceFrames, FrameProcessors

FILEPATH: Final = pathlib.Path(__file__)
FRAMES_DIR: Final = FILEPATH.parent / "frames"

class BenchResetReferenceFrames(ReferenceFrameEnum):
    HANG_OUT_HERE = ReferenceFrames.template_from_path(
        threshold=0.01,
        filepath=FRAMES_DIR / "hang-out-here.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(363, 593, 328, 23),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    WHAT_A_NICE_BENCH = ReferenceFrames.template_from_path(
        threshold=0.01,
        filepath=FRAMES_DIR / "what-a-nice-bench.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(361, 599, 215, 17),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
