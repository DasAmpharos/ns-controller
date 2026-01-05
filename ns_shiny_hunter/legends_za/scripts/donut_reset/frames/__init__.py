import pathlib
from typing import Final

from ns_shiny_hunter.frame import ReferenceFrameEnum, ReferenceFrames, FrameProcessors

FILE_PATH: Final = pathlib.Path(__file__)
DIR: Final = FILE_PATH.parent


class DonutResetReferenceFrames(ReferenceFrameEnum):
    TITLE_SCREEN = ReferenceFrames.logging(
        'TITLE_SCREEN',
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "title-screen.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((557, 576), (724, 602)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT,
            ),
            preprocessed=False
        ),
        False
    )
    LOAD_BACKUP_DATA = ReferenceFrames.logging(
        'LOAD_BACKUP_DATA',
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "load-backup-data.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((221, 138), (480, 157)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT
            ),
            preprocessed=False
        ),
        False
    )
    MAP_HOTEL_Z = ReferenceFrames.logging(
        'MAP_HOTEL_Z',
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "map-hotel-z.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((834, 126), (934, 156)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT
            ),
            preprocessed=False
        ),
        False
    )
    BERRY_SELECTION = ReferenceFrames.logging(
        'BERRY_SELECTION',
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "berry-selection.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((25, 131), (57, 163)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT
            ),
            preprocessed=False
        ),
        False
    )
    HYPER_TANGA_BERRY = ReferenceFrames.logging(
        'HYPER_TANGA_BERRY',
        ReferenceFrames.template_from_path(
            threshold=0.95,
            filepath=DIR / "hyper-tanga-berry.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((85, 248), (224, 270)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT
            ),
            preprocessed=False
        ),
        False
    )
    HYPER_KASIB_BERRY = ReferenceFrames.logging(
        'HYPER_KASIB_BERRY',
        ReferenceFrames.template_from_path(
            threshold=0.95,
            filepath=DIR / "hyper-kasib-berry.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((85, 372), (290, 414)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT
            ),
            preprocessed=False
        )
    )
    DONUT_INFO = ReferenceFrames.logging(
        'DONUT_INFO',
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "donut-info.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((47, 401), (91, 513)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT
            ),
            preprocessed=False
        ),
        False
    )
    DONUT_INFO_READY = ReferenceFrames.logging(
        'DONUT_INFO_READY',
        ReferenceFrames.template_from_path(
            threshold=0.9,
            filepath=DIR / "donut-info.jpg",
            frame_processor=FrameProcessors.all(
                FrameProcessors.crop_points((1180, 682), (1200, 703)),
                FrameProcessors.CVT_COLOR_BGR2GRAY,
                FrameProcessors.GAUSSIAN_BLUR_DEFAULT,
                FrameProcessors.ADAPTIVE_THRESHOLD_DEFAULT,
                FrameProcessors.MEDIAN_BLUR_DEFAULT
            ),
            preprocessed=False
        ),
        False
    )
