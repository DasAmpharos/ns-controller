import pathlib
from typing import Final

from ns_shiny_hunter.frame import ReferenceFrameEnum, ReferenceFrames, FrameProcessors, CompositeReferenceFrame

FILEPATH: Final = pathlib.Path(__file__)
DIR: Final = FILEPATH.parent


class LoadingScreenReferenceFrames(ReferenceFrameEnum):
    TURTWIG = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=DIR / "loading-screen.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(x=1156, y=659, w=29, h=40),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    CHIMCHAR = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=DIR / "loading-screen.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(x=1192, y=653, w=25, h=46),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    PIPLUP = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=DIR / "loading-screen.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(x=1225, y=661, w=30, h=38),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )


class BattleScreenReferenceFrames(ReferenceFrameEnum):
    BATTLE = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=DIR / "battle-screen.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(x=1043, y=432, w=65, h=24),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    POKEMON = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=DIR / "battle-screen.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(x=1043, y=510, w=102, h=24),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    BAG = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=DIR / "battle-screen.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(x=1043, y=588, w=40, h=24),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )
    RUN = ReferenceFrames.template_from_path(
        threshold=0.1,
        filepath=DIR / "battle-screen.jpg",
        frame_processor=FrameProcessors.all(
            FrameProcessors.crop_rect(x=1043, y=666, w=40, h=24),
            FrameProcessors.CVT_COLOR_BGR2GRAY,
            FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
            FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
        )
    )


class BdspReferenceFrames(ReferenceFrameEnum):
    LOADING_SCREEN = ReferenceFrames.composite(
        CompositeReferenceFrame.Mode.OR,
        *[
            LoadingScreenReferenceFrames.TURTWIG,
            LoadingScreenReferenceFrames.CHIMCHAR,
            LoadingScreenReferenceFrames.PIPLUP
        ],
    )
    BATTLE_SCREEN = ReferenceFrames.composite(
        CompositeReferenceFrame.Mode.AND,
        *[
            BattleScreenReferenceFrames.BATTLE,
            BattleScreenReferenceFrames.POKEMON,
            BattleScreenReferenceFrames.BAG,
            BattleScreenReferenceFrames.RUN
        ],
    )
    TITLE_SCREEN = ReferenceFrames.logging(
        "TITLE_SCREEN",
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "title-screen.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((497, 366), (781, 499)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.gaussian_blur((5, 5), 0.5, 0.5),
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT
            ),
            preprocessed=False
        )
    )
