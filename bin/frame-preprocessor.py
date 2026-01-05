import time

import cv2

from ns_shiny_hunter.bdsp.scripts.ramanas_park.rayquaza.frames import RayquazaReferenceFrames
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import ENTER_ICON_TEMPLATE
from ns_shiny_hunter.legends_za.scripts.donut_reset.frames import DonutResetReferenceFrames
from ns_shiny_hunter.legends_za.scripts.donut_reset.script import DonutResetScript

if __name__ == '__main__':
    # with FrameGrabber(0, imshow=False) as frame_grabber:
    #     time.sleep(3.0)
    #     try:
    #         while True:
    #             # DonutResetReferenceFrames.HYPER_TANGA_BERRY.matches(frame_grabber.frame)
    #             e1, e2, e3 = DonutResetScript.extract_effects(frame_grabber.frame)
    #             print(f"Effect1: {e1}, Effect2: {e2}, Effect3: {e3}")
    #     except KeyboardInterrupt:
    #         cv2.destroyAllWindows()
    #         pass

    frame = cv2.imread('ns_shiny_hunter/legends_za/scripts/donut_reset/frames/donut-info.jpg')
    e1, e2, e3 = DonutResetScript.extract_effects(frame)
    print(f"Effect1: {e1}, Effect2: {e2}, Effect3: {e3}")


    # for ref_frame in RayquazaReferenceFrames:
    #     if not ref_frame.value.delegate.preprocessed:
    #         cv2.imwrite(f'{ref_frame.name.lower()}.png', ref_frame.value.delegate.template)

    # frames_dir = pathlib.Path(__file__).parent.parent / "frames"
    # frames_dir.mkdir(parents=True, exist_ok=True)
    # for ref_frame in LegendsZAReferenceFrames:
    #     template = getattr(ref_frame.value, 'template')
    #     if hasattr(ref_frame.value, 'frame_processor'):
    #         print(f"Processing frame for {ref_frame.name}...")
    #         frame_processor: FrameProcessor = getattr(ref_frame.value, 'frame_processor')
    #         template = frame_processor.process_frame(template)
    #     cv2.imwrite(str(frames_dir / f"{ref_frame.name.lower()}.png"), template)
