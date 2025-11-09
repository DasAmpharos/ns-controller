from ns_shiny_hunter.frame import ReferenceFrameEnum, SimpleFrameProcessor, CompositeReferenceFrame, \
    SimpleReferenceFrame


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


class BenchResetReferenceFrames(ReferenceFrameEnum):
    HANG_OUT_HERE = SimpleReferenceFrame.create_from_file(
        __file__, "hang-out-here.jpg",
        SimpleFrameProcessor(x=363, y=593, w=328, h=23)
    )
    OVERWORLD = CompositeReferenceFrame(
        CompositeReferenceFrame.Behavior.OR,
        (
            OverworldReferenceFrames.DAY,
            OverworldReferenceFrames.NIGHT
        )
    )
    WHAT_A_NICE_BENCH = SimpleReferenceFrame.create_from_file(
        __file__, "what-a-nice-bench.jpg",
        SimpleFrameProcessor(x=361, y=599, w=215, h=17),
    )
