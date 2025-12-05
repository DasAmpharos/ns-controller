import cv2

from ns_shiny_hunter.bdsp.scripts.ramanas_park.rayquaza.frames import RayquazaReferenceFrames

if __name__ == '__main__':
    for ref_frame in RayquazaReferenceFrames:
        if not ref_frame.value.delegate.preprocessed:
            cv2.imwrite(f'{ref_frame.name.lower()}.png', ref_frame.value.delegate.template)

    # frames_dir = pathlib.Path(__file__).parent.parent / "frames"
    # frames_dir.mkdir(parents=True, exist_ok=True)
    # for ref_frame in LegendsZAReferenceFrames:
    #     template = getattr(ref_frame.value, 'template')
    #     if hasattr(ref_frame.value, 'frame_processor'):
    #         print(f"Processing frame for {ref_frame.name}...")
    #         frame_processor: FrameProcessor = getattr(ref_frame.value, 'frame_processor')
    #         template = frame_processor.process_frame(template)
    #     cv2.imwrite(str(frames_dir / f"{ref_frame.name.lower()}.png"), template)
