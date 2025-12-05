import time
from dataclasses import dataclass

from loguru import logger

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter import util
from ns_shiny_hunter.frame import ReferenceFrame
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.system.frames import Switch2ReferenceFrames


@dataclass(frozen=True)
class ScriptFrames:
    location: ReferenceFrame
    pokemon_in_battle: ReferenceFrame
    target_appeared: ReferenceFrame
    target_dialog: ReferenceFrame


class RamanasParkScript:
    def __init__(self,
                 controller: NsControllerClient,
                 frame_grabber: FrameGrabber,
                 script_frames: ScriptFrames,
                 baseline: list[float],
                 resets: int = 0):
        self.controller = controller
        self.frame_grabber = frame_grabber
        self.script_frames = script_frames
        self.encounter_times = baseline
        self.resets = resets

    def run(self, capture_baseline: bool = False):
        software_errors = 132
        try:
            while True:
                self.resets += 1
                logger.info(f"Reset #{self.resets}...")
                # while not BdspReferenceFrames.TITLE_SCREEN.matches(self.frame_grabber.frame):
                #     self.controller.click(Button.A)
                # while BdspReferenceFrames.TITLE_SCREEN.matches(self.frame_grabber.frame):
                #     self.controller.click(Button.A)
                # while not self.script_frames.location.matches(self.frame_grabber.frame):
                #     time.sleep(1 / self.frame_grabber.fps)
                while not self.script_frames.target_appeared.matches(self.frame_grabber.frame):
                    if Switch2ReferenceFrames.SOFTWARE_ERROR.matches(self.frame_grabber.frame):
                        software_errors += 1
                        logger.info(f"Software error #{software_errors} occurred")
                    self.controller.click(Button.A, post_delay=0.15)

                appeared_at = time.perf_counter()
                # capture brightness values until Pokemon in battle detected
                brightness_values = []
                while not self.script_frames.pokemon_in_battle.matches(self.frame_grabber.frame):
                    brightness_values.append(util.get_brightness(self.frame_grabber.frame))
                    time.sleep(1 / self.frame_grabber.fps)
                pokemon_in_battle_at = time.perf_counter()

                time_delta = pokemon_in_battle_at - appeared_at
                brightness_delta = max(brightness_values) - min(brightness_values)
                logger.info(f"Encounter took {time_delta:.3f}s; Brightness delta: {brightness_delta:.3f}")
                if util.is_outlier(time_delta, self.encounter_times):
                    self.controller.click(Button.HOME, down=1.5)
                    self.controller.click(Button.A)
                    break
                self.controller.click(Button.HOME, post_delay=1.2)
                self.controller.click(Button.X)
        except KeyboardInterrupt:
            print(f"\nExiting script after {self.resets} resets...")
            print(f"Completed {self.resets} resets with {software_errors} software errors.")
