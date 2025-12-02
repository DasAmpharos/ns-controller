import json
import time
from collections import deque
from dataclasses import dataclass

from InquirerPy import inquirer
from loguru import logger

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter import util
from ns_shiny_hunter.frame import ReferenceFrame
from ns_shiny_hunter.frame_grabber import FrameGrabber


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
        self.encounter_times = deque(baseline, maxlen=250)
        self.resets = resets

    def run(self, capture_baseline: bool = False):
        try:
            while True:
                self.resets += 1
                print(f"Reset #{self.resets}...")
                while not self.script_frames.target_appeared.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)

                appeared_at = time.perf_counter()
                # capture brightness values until Pokemon in battle detected
                brightness_values = []
                while not self.script_frames.pokemon_in_battle.matches(self.frame_grabber.frame):
                    brightness_values.append(util.get_brightness(self.frame_grabber.frame))
                    time.sleep(1 / self.frame_grabber.fps)
                pokemon_in_battle_at = time.perf_counter()

                time_delta = pokemon_in_battle_at - appeared_at
                logger.info(f"Encounter took {time_delta:.3f}s")
                brightness_delta = max(brightness_values) - min(brightness_values)
                logger.info(f"Brightness delta: {brightness_delta:.3f}")
                self.encounter_times.append(time_delta)
                if capture_baseline:
                    prompt = inquirer.confirm(message='Is this a shiny?')
                    if prompt.execute():
                        break
                    elif len(self.encounter_times) >= 10:
                        with open('baseline.json', 'w') as file:
                            json.dump(list(self.encounter_times), file)
                        break
                elif util.is_outlier(time_delta, self.encounter_times) and brightness_delta >= 50:
                    self.controller.click(Button.HOME, down=1.5)
                    self.controller.click(Button.A)
                    break
                self.controller.click(Button.HOME, post_delay=1.2)
                self.controller.click(Button.X)
        except KeyboardInterrupt:
            print(f"\nExiting script after {self.resets} resets...")
