import pathlib
from typing import Final

import cv2

from ns_shiny_hunter.frame import ReferenceFrameEnum, ReferenceFrames, FrameProcessors

FILEPATH: Final = pathlib.Path(__file__)
DIR: Final = FILEPATH.parent / "preprocessed"


class RayquazaReferenceFrames(ReferenceFrameEnum):
    LOCATION = ReferenceFrames.logging(
        "LOCATION",
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "location.png",
            flags=cv2.IMREAD_GRAYSCALE,
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((196, 32), (401, 75)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.gaussian_blur((5, 5), 0.5, 0.5),
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
            ),
            # preprocessed=False
        ),
        False
    )
    TARGET_DIALOG = ReferenceFrames.logging(
        "TARGET_DIALOG",
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "target-dialog.png",
            flags=cv2.IMREAD_GRAYSCALE,
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((293, 603), (517, 647)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.gaussian_blur((5, 5), 0.5, 0.5),
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
            ),
            # preprocessed=False
        ),
        False
    )
    TARGET_APPEARED = ReferenceFrames.logging(
        "TARGET_APPEARED",
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "target-appeared.png",
            flags=cv2.IMREAD_GRAYSCALE,
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((113, 603), (405, 647)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.gaussian_blur((5, 5), 0.5, 0.5),
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
            ),
            # preprocessed=False
        ),
        False
    )
    POKEMON_IN_BATTLE = ReferenceFrames.logging(
        "POKEMON_IN_BATTLE",
        ReferenceFrames.template_from_path(
            threshold=0.85,
            filepath=DIR / "pokemon-in-battle.png",
            flags=cv2.IMREAD_GRAYSCALE,
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((113, 603), (201, 635)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.gaussian_blur((5, 5), 0.5, 0.5),
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
            ),
            # preprocessed=False
        ),
        False
    )
