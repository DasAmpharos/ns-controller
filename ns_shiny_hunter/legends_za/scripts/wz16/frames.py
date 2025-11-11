from ns_shiny_hunter.frame import SimpleReferenceFrame, SimpleFrameProcessor, ReferenceFrameEnum, LoggingReferenceFrame


class WildZone16ReferenceFrames(ReferenceFrameEnum):
    PRESS_A_TO_ENTER = LoggingReferenceFrame(
        name="PRESS_A_TO_ENTER",
        delegate=SimpleReferenceFrame.create_from_file(
            __file__, "press-a-to-enter.jpg",
            SimpleFrameProcessor.from_points((693, 418), (709, 433)),
            threshold=10
        )
    )
