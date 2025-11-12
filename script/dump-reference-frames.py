import pathlib

import cv2

from ns_shiny_hunter.frame import FrameProcessor, LoggingReferenceFrame
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames

if __name__ == '__main__':
    framepath = pathlib.Path(__file__).parent.parent / "ns_shiny_hunter" / "legends_za" / "scripts" / "bench_reset" / "frames" / "what-a-nice-bench.jpg"
    frame = cv2.imread(str(framepath), cv2.IMREAD_COLOR_BGR)

    ref_frame = LoggingReferenceFrame(name='test', delegate=LegendsZAReferenceFrames.OVERWORLD)
    frame_processor: FrameProcessor = getattr(LegendsZAReferenceFrames.OVERWORLD.value, "frame_processor")
    cv2.imshow("frame", frame_processor.process_frame(frame))
    cv2.imshow("template", ref_frame.delegate.value.template)
    cv2.waitKey(0)

    ref_frame.get_percent_match(frame)
    cv2.destroyAllWindows()


    # frames_dir = pathlib.Path(__file__).parent.parent / "frames"
    # frames_dir.mkdir(parents=True, exist_ok=True)
    # for ref_frame in LegendsZAReferenceFrames:
    #     template = getattr(ref_frame.value, 'template')
    #     if hasattr(ref_frame.value, 'frame_processor'):
    #         print(f"Processing frame for {ref_frame.name}...")
    #         frame_processor: FrameProcessor = getattr(ref_frame.value, 'frame_processor')
    #         template = frame_processor.process_frame(template)
    #     cv2.imwrite(str(frames_dir / f"{ref_frame.name.lower()}.png"), template)