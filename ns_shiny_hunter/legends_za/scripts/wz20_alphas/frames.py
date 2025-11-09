import pathlib
from typing import Final

from ns_shiny_hunter.frame import ReferenceFrameEnum, SimpleFrameProcessor, SimpleReferenceFrame

filepath: Final = pathlib.Path(__file__)


class ReferenceFrames(ReferenceFrameEnum):
    HANG_OUT_HERE = SimpleReferenceFrame.create_from_path(
        filepath.parent.parent / "bench_reset" / "frames" / "hang-out-here.jpg",
        SimpleFrameProcessor(x=363, y=593, w=328, h=23)
    )
    WHAT_A_NICE_BENCH = SimpleReferenceFrame.create_from_path(
        filepath.parent.parent / "bench_reset" / "frames" / "what-a-nice-bench.jpg",
        SimpleFrameProcessor(x=361, y=599, w=215, h=17),
    )
