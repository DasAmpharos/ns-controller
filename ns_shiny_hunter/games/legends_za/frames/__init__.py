import pathlib
from typing import Final

import cv2
import numpy as np

from ns_shiny_hunter.frame import FrameProcessors, ReferenceFrameEnum, ReferenceFrames

FILEPATH: Final = pathlib.Path(__file__)
DIR: Final = FILEPATH.parent


class LegendsZAReferenceFrames(ReferenceFrameEnum):
    OPEN_MAP = ReferenceFrames.logging(
        name='OPEN_MAP',
        delegate=ReferenceFrames.template_from_path(
            threshold=0.9,
            flags=cv2.IMREAD_GRAYSCALE,
            filepath=DIR / "open-map.png",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_rect(57, 25, 123, 21),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
            )
        ),
        enabled=False
    )
    TRAVEL_HERE = ReferenceFrames.template_from_path(
        threshold=0.01,
        flags=cv2.IMREAD_GRAYSCALE,
        filepath=DIR / "travel-here.png",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(582, 425, 107, 21),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    OVERWORLD = ReferenceFrames.template_from_path(
        threshold=0.44,
        filepath=DIR / "overworld.png",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_polygon(
                np.array(
                    dtype=np.int32,
                    object=[
                        [121, 109],
                        [130, 131],
                        [121, 128],
                        [120, 128],
                        [111, 131],
                        [120, 109],
                    ]
                )
            ),
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT
        ),
    )
    PRESS_A = ReferenceFrames.template_match_from_path(
        threshold=0.85,
        flags=cv2.IMREAD_GRAYSCALE,
        filepath=DIR / "press-a.png",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(688, 416, 28, 720 - 416),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    PRESS_A_TO_ENTER = ReferenceFrames.template_from_path(
        threshold=0.85,
        flags=cv2.IMREAD_GRAYSCALE,
        filepath=DIR / "press-a.png",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_points((692, 414), (709, 431)),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    PRESS_A_TO_TALK = ReferenceFrames.template_from_path(
        threshold=0.85,
        flags=cv2.IMREAD_GRAYSCALE,
        filepath=DIR / "press-a.png",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_points((692, 423), (709, 440)),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )

WIDTH: Final = 1280
HEIGHT: Final = 720
CENTER_X: Final = WIDTH // 2
CENTER_Y: Final = HEIGHT // 2

ENTER_ICON_TEMPLATE: Final = ReferenceFrames.template_match_from_path(
    filepath=DIR / "enter-icon.png",
    threshold=0.70,
    flags=cv2.IMREAD_GRAYSCALE,
    frame_processor=FrameProcessors.all(
        FrameProcessors.crop_rect(CENTER_X - WIDTH // 4, CENTER_Y + HEIGHT // 4, WIDTH // 2, HEIGHT // 2),
        FrameProcessors.CVT_COLOR_BGR2GRAY
    ),
)
