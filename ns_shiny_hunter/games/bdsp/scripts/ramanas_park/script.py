import json
import os
import pathlib
import time
from dataclasses import dataclass

import cv2
import dotenv
import requests
from InquirerPy import inquirer
from loguru import logger

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter import util
from ns_shiny_hunter.frame import Frame, ReferenceFrame
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.system.frames import Switch2ReferenceFrames

dotenv.load_dotenv()


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
                 software_errors: int = 0,
                 resets: int = 0):
        self.controller = controller
        self.frame_grabber = frame_grabber
        self.script_frames = script_frames
        self.encounter_times = baseline
        self.software_errors = software_errors
        self.resets = resets

    def run(self, capture_baseline: bool = False):
        try:
            while True:
                self.resets += 1
                logger.info(f"Reset #{self.resets}...")
                while not self.script_frames.target_appeared.matches(self.frame_grabber.frame):
                    if Switch2ReferenceFrames.SOFTWARE_ERROR.matches(self.frame_grabber.frame):
                        self.software_errors += 1
                        logger.info(f"Software error #{self.software_errors} occurred")
                    self.controller.click(Button.A, post_delay=0.15)

                appeared_at = time.perf_counter()
                target_appeared_frame = self.frame_grabber.frame

                # capture brightness values until Pokemon in battle detected
                brightness_values = []
                while not self.script_frames.pokemon_in_battle.matches(self.frame_grabber.frame):
                    brightness_values.append(util.get_brightness(self.frame_grabber.frame))
                    time.sleep(1 / self.frame_grabber.fps)
                pokemon_in_battle_at = time.perf_counter()

                time_delta = pokemon_in_battle_at - appeared_at
                brightness_delta = max(brightness_values) - min(brightness_values)
                logger.info(f"Encounter took {time_delta:.3f}s; Brightness delta: {brightness_delta:.3f}")

                if self.handle_encounter(capture_baseline, target_appeared_frame, time_delta, brightness_delta):
                    break
                self.controller.click(Button.HOME, post_delay=1.2)
                self.controller.click(Button.X)
        except KeyboardInterrupt:
            print(f"\nExiting script after {self.resets} resets...")
            print(f"Completed {self.resets} resets with {self.software_errors} software errors.")

    def handle_encounter(self,
                         capture_baseline: bool,
                         target_appeared_frame: Frame,
                         delta_t: float,
                         delta_b: float) -> bool:
        if capture_baseline:
            self.encounter_times.append(delta_t)
            prompt = inquirer.confirm(message='Is this a shiny?')
            if prompt.execute():
                return True
            if len(self.encounter_times) >= 10:
                with open('baseline.json', 'w') as file:
                    json.dump(self.encounter_times, file)
                return True
            return False

        if util.is_outlier(delta_t, self.encounter_times):
            filepath = pathlib.Path("shiny.png")
            cv2.imwrite(str(filepath), target_appeared_frame)
            response = requests.post('https://api.pushover.net/1/messages.json', data={
                'token': os.environ['PUSHOVER_API_TOKEN'],
                'user': os.environ['PUSHOVER_USER_KEY'],
                'message': '\n'.join([
                    f'Possible shiny found after {self.resets} encounters!',
                    f'Brightness delta: {delta_b:.3f}'
                    f'Encounter took {delta_t:.3f}s'
                ])
            }, files={
                'attachment': (filepath.name, filepath.read_bytes(), 'image/png')
            })
            logger.info(response.text)

            time.sleep(15)
            self.controller.click(Button.CAPTURE, down=3.0, post_delay=1.0)
            self.controller.click(Button.HOME, down=1.5)
            self.controller.click(Button.A)
            return True
        return False
