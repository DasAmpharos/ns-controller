import pathlib
from typing import Final

from ns_shiny_hunter.frame import ReferenceFrameEnum, ReferenceFrames, FrameProcessors

FILEPATH: Final = pathlib.Path(__file__)
FRAMES_DIR: Final = FILEPATH.parent / "frames"


class RayquazaReferenceFrames(ReferenceFrameEnum):
    LOCATION = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=FRAMES_DIR / "target-location.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_points((196, 32), (401, 75)),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    TARGET_DIALOG = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=FRAMES_DIR / "target-dialog.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_points((293, 603), (517, 647)),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    TARGET_APPEARED = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=FRAMES_DIR / "target-appeared.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_points((113, 603), (405, 647)),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    POKEMON_IN_BATTLE = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=FRAMES_DIR / "pokemon-in-battle.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_points((113, 603), (350, 647)),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
