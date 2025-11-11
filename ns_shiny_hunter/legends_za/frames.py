import numpy as np

from ns_shiny_hunter.frame import (
    ReferenceFrameEnum,
    SimpleFrameProcessor,
    PolygonFrameProcessor, SimpleReferenceFrame
)


class OverworldReferenceFrames(ReferenceFrameEnum):
    DAY = SimpleReferenceFrame.create_from_file(
        __file__, "overworld-day.jpg",
        SimpleFrameProcessor(x=110, y=110, w=22, h=22),
        threshold=25
    )
    NIGHT = SimpleReferenceFrame.create_from_file(
        __file__, "overworld-night.jpg",
        SimpleFrameProcessor(x=110, y=110, w=22, h=22),
        threshold=25
    )


class LegendsZAReferenceFrames(ReferenceFrameEnum):
    OPEN_MAP = SimpleReferenceFrame.create_from_file(
        __file__, "open-map.jpg",
        SimpleFrameProcessor(x=57, y=25, w=123, h=21),
        threshold=5
    )
    TRAVEL_HERE = SimpleReferenceFrame.create_from_file(
        __file__, "travel-here.jpg",
        SimpleFrameProcessor(x=582, y=425, w=107, h=21)
    )
    OVERWORLD = SimpleReferenceFrame.create_from_file(
        __file__, "overworld-day.jpg",
        PolygonFrameProcessor(points=np.array([[121, 109], [131, 132], [121, 129], [110, 132]], dtype=np.int32)),
        threshold=65
    )
    PRESS_A_TO_ENTER = SimpleReferenceFrame.create_from_file(
        __file__, "press-a-to-enter.jpg",
        SimpleFrameProcessor.from_points((692, 414), (709, 431))
    )
    PRESS_A_TO_TALK = SimpleReferenceFrame.create_from_file(
        __file__, "press-a-to-talk.jpg",
        SimpleFrameProcessor.from_points((692, 423), (709, 438))
    )
