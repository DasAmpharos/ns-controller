import time

import cv2

from ns_shiny_hunter.frame import LoggingReferenceFrame, FrameProcessors
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames
from ns_shiny_hunter.legends_za.scripts.litwick.frames import LitwickScriptReferenceFrames


def main():
    reference_frames = [LoggingReferenceFrame(name=it.name, delegate=it) for it in LitwickScriptReferenceFrames]
    reference_frame = next(iter([it for it in reference_frames if it.name == "FRAME_1"]))

    frame_processor = reference_frame.delegate.value.frame_processor
    frame = frame_processor.process_frame(reference_frame.delegate.value.template)
    cv2.imwrite("frame-1.jpg", frame)

    # with FrameGrabber(0, imshow=False) as frame_grabber:
    #     try:
    #         while True:
    #             time.sleep(0.1)
    #             print("Grabbing frame...")
    #             frame = frame_grabber.frame
    #             if frame is not None:
    #                 print("Comparing frame...")
    #                 reference_frame.matches(frame)
    #                 # for reference_frame in reference_frames:
    #                 #     reference_frame.get_percent_match(frame)
    #             else:
    #                 print("No frame grabbed...")
    #     except KeyboardInterrupt:
    #         pass


if __name__ == '__main__':
    main()
