import pathlib
from typing import Final

from ns_shiny_hunter.frame import FrameProcessors, ReferenceFrameEnum, ReferenceFrames

FILE_PATH: Final = pathlib.Path(__file__)
FRAMES_DIR: Final = FILE_PATH.parent


class HyperspaceReferenceFrames(ReferenceFrameEnum):
    MAP = ReferenceFrames.logging(
        name='HyperspaceReferenceFrames.MAP',
        delegate=ReferenceFrames.template_from_path(
            threshold=0.75,
            filepath=FRAMES_DIR / "map.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((41, 21), (628, 50)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
            ),
            preprocessed=False
        )
    )
    PROMPT_TO_LEAVE = ReferenceFrames.logging(
        name='HyperspaceReferenceFrames.PROMPT_TO_LEAVE',
        delegate=ReferenceFrames.template_from_path(
            threshold=0.8,
            filepath=FRAMES_DIR / "prompt-to-leave.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((362, 591), (850, 624)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
            ),
            preprocessed=False
        )
    )
    SPOTTED = ReferenceFrames.logging(
        name='HyperspaceReferenceFrames.SPOTTED',
        delegate=ReferenceFrames.template_from_path(
            threshold=0.8,
            filepath=FRAMES_DIR / "spotted.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((359, 591), (752, 623)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
            ),
            preprocessed=False
        )
    )
