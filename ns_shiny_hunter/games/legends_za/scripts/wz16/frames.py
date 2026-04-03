from ns_shiny_hunter.frame import LoggingReferenceFrame, ReferenceFrameEnum, SimpleFrameProcessor, SimpleReferenceFrame


class WildZone16ReferenceFrames(ReferenceFrameEnum):
    PRESS_A_TO_ENTER = LoggingReferenceFrame(
        name="PRESS_A_TO_ENTER",
        delegate=SimpleReferenceFrame.create_from_file(
            __file__, "frames/press-a-to-enter.jpg",
            SimpleFrameProcessor.from_points((693, 418), (709, 433)),
            threshold=10
        )
    )
