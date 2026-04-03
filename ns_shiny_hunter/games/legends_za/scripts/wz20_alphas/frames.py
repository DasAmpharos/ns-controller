import pathlib
from typing import Final

from ns_shiny_hunter.frame import ReferenceFrameEnum, SimpleFrameProcessor, SimpleReferenceFrame

filepath: Final = pathlib.Path(__file__)


class ReferenceFrames(ReferenceFrameEnum):
    HANG_OUT_HERE = SimpleReferenceFrame.create_from_path(
        filepath.parent.parent / "bench_reset" / "frames" / "hang-out-here.jpg",
        SimpleFrameProcessor.from_points((363, 593), (691, 616)),
    )
    WHAT_A_NICE_BENCH = SimpleReferenceFrame.create_from_path(
        filepath.parent.parent / "bench_reset" / "frames" / "what-a-nice-bench.jpg",
        SimpleFrameProcessor.from_points((361, 599), (576, 616)),
    )
