import re
import time
from typing import Final

import pytesseract

from ns_controller.client.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame import Frame, FrameProcessors
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames
from ns_shiny_hunter.legends_za.scripts.donut_reset.frames import DonutResetReferenceFrames


class Ingredient:
    name: str
    quantity: int


class DonutResetScript:
    ALPHA_POWER_RE: Final = re.compile(r'Alpha Power \(Lv. ([1-3])\)')
    SPARKLING_POWER_RE: Final = re.compile(r'Sparkling Power: (.*) \(Lv. ([1-3])\)')
    EFFECT_PROCESSOR: Final = FrameProcessors.all(
        FrameProcessors.CVT_COLOR_BGR2GRAY,
        FrameProcessors.GAUSSIAN_BLUR_DEFAULT
    )
    PYTESSERACT_CONFIG: Final = "--oem 3 --psm 7 -c tessedit_char_whitelist=\" .:()123ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz\""

    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerClient, targets: list[str],
                 resets: int = 0):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.targets = targets
        self.resets = resets

    def run(self):
        try:
            while True:
                self.resets += 1
                print(f"Reset #{self.resets}...")
                # Turbo A until on title screen
                while not DonutResetReferenceFrames.TITLE_SCREEN.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)
                # Load backup data
                time.sleep(0.5)
                self.controller.click(Button.B, Button.X, Button.DPAD_UP, post_delay=0.5)
                while DonutResetReferenceFrames.LOAD_BACKUP_DATA.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)
                # Open map
                while not LegendsZAReferenceFrames.OPEN_MAP.matches(self.frame_grabber.frame):
                    self.controller.click(Button.PLUS, post_delay=0.25)
                # Select Hotel Z on map and fast travel
                time.sleep(0.5)
                self.controller.click(Button.Y, post_delay=0.5)
                while not DonutResetReferenceFrames.MAP_HOTEL_Z.matches(self.frame_grabber.frame):
                    self.controller.click(Button.DPAD_DOWN)
                while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)
                # enter Hotel Z
                self.controller.click(Button.Y, post_delay=1.5)
                self.controller.click(Button.A)
                time.sleep(3.0)
                # Walk up to Ansha's Donuts
                self.controller.set_stick(ls_y=1)
                self.controller.press(Button.B, post_delay=1.5)
                self.controller.set_stick(ls_y=0.0, ls_x=-1.0, post_delay=0.5)
                self.controller.clear()
                # Interact with Ansha's Donuts
                while not DonutResetReferenceFrames.BERRY_SELECTION.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A, post_delay=0.25)

                # Navigate to Hyper Tanga Berry
                while not DonutResetReferenceFrames.HYPER_TANGA_BERRY.matches(self.frame_grabber.frame):
                    self.controller.click(Button.DPAD_UP, down=0.05, post_delay=0.2)
                # Select 4 Hyper Tanga Berries
                time.sleep(0.5)
                for _ in range(4):
                    self.controller.click(Button.A)
                # Navigate to Hyper Payapa Berry
                # self.controller.click(Button.DPAD_UP)
                # Navigate to Hyper Kasib Berry
                for _ in range(2):
                    self.controller.click(Button.DPAD_DOWN)
                # Select 4 Berries
                for _ in range(4):
                    self.controller.click(Button.A)
                # Make the donut
                self.controller.click(Button.PLUS)
                # Turbo A until on Donut Info screen
                while not DonutResetReferenceFrames.DONUT_INFO.matches(self.frame_grabber.frame):
                    self.controller.click(Button.A)
                while not DonutResetReferenceFrames.DONUT_INFO_READY.matches(self.frame_grabber.frame):
                    time.sleep(0.1)
                # Extract the donut effects
                effects = self.extract_effects(self.frame_grabber.frame)
                alpha_power_effect = self.get_alpha_power_effect(effects)
                sparkling_power_effect = self.get_sparkling_power_effect(effects)

                print(f"> Donut Effects: {effects}")
                print(f'  > Alpha Power Effect: {alpha_power_effect}')
                print(f'  > Sparkling Power Effect: {sparkling_power_effect}')
                if self.target_found(sparkling_power_effect, alpha_power_effect):
                    break
                self.controller.click(Button.HOME, post_delay=1.2)
                self.controller.click(Button.X)
        except KeyboardInterrupt:
            print(f"\nCompleted {self.resets} resets.")
            raise

    @classmethod
    def crop_effects(cls, frame: Frame) -> tuple[Frame, Frame, Frame]:
        e1_frame = cls.EFFECT_PROCESSOR.process_frame(frame[548:579, 155:503])
        e2_frame = cls.EFFECT_PROCESSOR.process_frame(frame[580:611, 155:503])
        e3_frame = cls.EFFECT_PROCESSOR.process_frame(frame[613:643, 155:503])
        return e1_frame, e2_frame, e3_frame

    @classmethod
    def extract_effects(cls, frame) -> tuple[str, str, str]:
        f1, f2, f3 = cls.crop_effects(frame)
        e1 = pytesseract.image_to_string(f1, lang='eng', config=cls.PYTESSERACT_CONFIG)
        e2 = pytesseract.image_to_string(f2, lang='eng', config=cls.PYTESSERACT_CONFIG)
        e3 = pytesseract.image_to_string(f3, lang='eng', config=cls.PYTESSERACT_CONFIG)
        return e1.strip(), e2.strip(), e3.strip()

    @classmethod
    def get_alpha_power_effect(cls, effects: tuple[str, str, str]) -> int | None:
        for effect in effects:
            result = cls.ALPHA_POWER_RE.match(effect)
            if result:
                return int(result.group(1))
        return None

    @classmethod
    def get_sparkling_power_effect(cls, effects: tuple[str, str, str]) -> tuple[str, int] | None:
        for effect in effects:
            result = cls.SPARKLING_POWER_RE.match(effect)
            if result:
                effect_type = result.group(1)
                effect_level = result.group(2)
                return effect_type, int(effect_level)
        return None

    def target_found(self, sparkling_power_effect: tuple[str, int] | None, alpha_power_effect: int | None) -> bool:
        return ((sparkling_power_effect is not None
                 and sparkling_power_effect[0] in self.targets
                 and sparkling_power_effect[1] == 3)
                and (alpha_power_effect is not None
                     and alpha_power_effect >= 2))
