import time
from types import MappingProxyType
from typing import Final

import cv2
import numpy as np
import pytesseract

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame import Frame
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames
from ns_shiny_hunter.legends_za.scripts.sushi_high_roller.frames import SushiHighRollerReferenceFrames, \
    ATTACK_FRAME_PROCESSOR, POKEMON_CENTER_DIALOG_OPTIONS_FRAME_PROCESSOR, ITEM_NAME_FRAME_PROCESSOR, \
    ITEM_QUANTITY_FRAME_PROCESSOR, QUANTITY_TO_SELL_FRAME_PROCESSOR, ACCEPT_OFFER_FRAME_PROCESSOR
from ns_shiny_hunter.legends_za.scripts.sushi_high_roller.state import State


class SushiHighRoller:
    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerClient, state: State = State.ENTRANCE_1):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.state_handlers: Final = MappingProxyType({
            State.ENTRANCE_1: self.state_handler_entrance,
            State.ENTRANCE_2: self.state_handler_entrance,
            State.ENTRANCE_CONFIRMATION: self.state_handler_entrance_confirmation,
            State.FOLLOW_ME: self.state_handler_follow_me,
            State.BATTLE: self.state_handler_battle,
            State.OUTCOME_SUCCESS: self.state_handler_outcome,
            State.OUTCOME_FAILURE: self.state_handler_outcome,
            State.CANNOT_AFFORD: self.state_handler_cannot_afford,
            State.OPEN_MAP: self.state_handler_open_map,
            State.TRAVEL_TO_POKEMON_CENTER: self.state_handler_travel_here,
            State.TRAVEL_TO_POKEMON_CENTER_CONFIRMATION: self.state_handler_travel_to_pokemon_center_confirmation,
            State.OVERWORLD_POKEMON_CENTER: self.state_handler_overworld_pokemon_center,
            State.POKEMON_CENTER_DIALOG: self.state_handler_pokemon_center_dialog,
        })
        self.state = state

    def run(self):
        try:
            while True:
                state_handler = self.state_handlers.get(self.state, None)
                if state_handler is None:
                    print(f"No handler for state: {self.state}")
                    break
                state_handler()
        except KeyboardInterrupt:
            print(f"\nExiting SushiHighRoller script...")
            # self.controller.click([Button.HOME], down=1.5)
            # self.controller.click([Button.A])

    def state_handler_entrance(self):
        print(f'State.ENTRANCE_1 | State.ENTRANCE_2')
        if self.state == State.ENTRANCE_1:
            self.controller.set_stick(ls_x=1, post_delay=0.25)
            self.controller.set_stick(ls_x=0, post_delay=0.1)
        self.controller.click([Button.A])

        if SushiHighRollerReferenceFrames.ENTRANCE_CONFIRMATION.matches(self.frame_grabber.frame):
            self.state = State.ENTRANCE_CONFIRMATION

    def state_handler_entrance_confirmation(self):
        print('State.ENTRANCE_CONFIRMATION')
        self.controller.click([Button.A])

        frame = self.frame_grabber.frame
        if SushiHighRollerReferenceFrames.CANNOT_AFFORD.matches(frame):
            self.state = State.CANNOT_AFFORD
        elif SushiHighRollerReferenceFrames.FOLLOW_ME.matches(frame):
            self.state = State.FOLLOW_ME

    def state_handler_follow_me(self):
        print('State.FOLLOW_ME')
        self.controller.click([Button.A])
        if SushiHighRollerReferenceFrames.BATTLE.matches(self.frame_grabber.frame):
            self.state = State.BATTLE

    def state_handler_battle(self):
        print('State.BATTLE')
        if SushiHighRollerReferenceFrames.BATTLE.matches(self.frame_grabber.frame):
            frame = ATTACK_FRAME_PROCESSOR.prepare_frame(self.frame_grabber.frame)
            text = pytesseract.image_to_string(frame)
            text = text.strip().lower()
            print(f'> Detected attack: "{text}"')
            if text == "":
                self.controller.release([Button.ZL])
                self.controller.press([Button.ZL])
                time.sleep(0.5)
        self.controller.click([Button.A])

        frame = self.frame_grabber.frame
        if SushiHighRollerReferenceFrames.OUTCOME_FAILURE.matches(frame):
            self.state = State.OUTCOME_FAILURE
        elif SushiHighRollerReferenceFrames.OUTCOME_SUCCESS.matches(frame):
            self.state = State.OUTCOME_SUCCESS

    def state_handler_outcome(self):
        print('State.OUTCOME_FAILURE | State.OUTCOME_SUCCESS')
        self.controller.click([Button.A])
        if SushiHighRollerReferenceFrames.ENTRANCE_2.matches(self.frame_grabber.frame):
            self.state = State.ENTRANCE_2

    def state_handler_cannot_afford(self):
        print('State.CANNOT_AFFORD')
        while True:
            self.controller.click([Button.A])
            if SushiHighRollerReferenceFrames.ENTRANCE_2.matches(self.frame_grabber.frame):
                break

        # open map
        self.controller.click([Button.PLUS])
        if LegendsZAReferenceFrames.OPEN_MAP.matches(self.frame_grabber.frame):
            self.state = State.OPEN_MAP

    def state_handler_open_map(self):
        print('State.OPEN_MAP')
        self.controller.set_stick(ls_x=0.05, ls_y=0.8, post_delay=0.3)
        self.controller.clear(post_delay=1)
        if SushiHighRollerReferenceFrames.TRAVEL_TO_POKEMON_CENTER.matches(self.frame_grabber.frame):
            self.state = State.TRAVEL_TO_POKEMON_CENTER

    def state_handler_travel_here(self):
        print('State.TRAVEL_HERE')
        self.controller.click([Button.A])
        if SushiHighRollerReferenceFrames.TRAVEL_TO_POKEMON_CENTER_CONFIRMATION.matches(self.frame_grabber.frame):
            self.state = State.TRAVEL_TO_POKEMON_CENTER_CONFIRMATION

    def state_handler_travel_to_pokemon_center_confirmation(self):
        print('State.TRAVEL_TO_POKEMON_CENTER_CONFIRMATION')
        self.controller.click([Button.A])
        if LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
            self.state = State.OVERWORLD_POKEMON_CENTER

    def state_handler_overworld_pokemon_center(self):
        print('State.OVERWORLD_POKEMON_CENTER')
        self.controller.set_stick(ls_y=1, post_delay=0.1)
        self.controller.click([Button.B])
        while True:
            if SushiHighRollerReferenceFrames.POKEMON_CENTER_DIALOG_START.matches(self.frame_grabber.frame):
                self.state = State.POKEMON_CENTER_DIALOG
                break
            time.sleep(0.1)

    def state_handler_pokemon_center_dialog(self):
        print('State.POKEMON_CENTER_DIALOG')
        self.controller.click([Button.A], post_delay=2)
        self.controller.click([Button.A], post_delay=0.5)

        def select_option(option_index: int):
            while True:
                frame = POKEMON_CENTER_DIALOG_OPTIONS_FRAME_PROCESSOR.prepare_frame(self.frame_grabber.frame)
                if self.detect_highlighted_option(frame, 3) == option_index:
                    self.controller.click([Button.A])
                    break
                self.controller.click([Button.DPAD_DOWN], down=0.2)

        select_option(1)  # select "I'd like to do some shopping"
        select_option(1)  # select "I'd like to sell"

        while not SushiHighRollerReferenceFrames.SELL_TREASURES.matches(self.frame_grabber.frame):
            self.controller.click([Button.R], post_delay=0.5)

        self.sell_treasures()
        while True:
            self.controller.click([Button.B])
            if LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                break

    def sell_treasures(self):
        while True:
            time.sleep(0.1)
            item_name, item_quantity = self.detect_item(self.frame_grabber.frame)
            print(f'> Detected item: "{item_name}" x{item_quantity}')
            if item_name and item_quantity:
                # select item, select max quantity, offer items
                self.controller.click([Button.A], post_delay=1)
                self.controller.click([Button.DPAD_DOWN], post_delay=1)
                self.controller.click([Button.A], post_delay=1)
                self.controller.click([Button.A], post_delay=1)
                self.controller.click([Button.A], post_delay=1)
                continue
            break

    # Returns one of the three option strings
    @staticmethod
    def detect_highlighted_option(frame: Frame, n_options: int) -> int:
        # --- 2) Mask "white" (selected row background) in HSV ---
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        white_lo = np.array([0, 0, 210], np.uint8)  # low saturation, high value
        white_hi = np.array([179, 70, 255], np.uint8)
        white_mask = cv2.inRange(hsv, white_lo, white_hi)

        # Small cleanups (optional, but helps on video)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_OPEN, k)
        white_mask = cv2.morphologyEx(white_mask, cv2.MORPH_CLOSE, k)

        # --- 3) Split panel into equal-height bands and score by white coverage ---
        h, w = frame.shape[:2]
        bands = np.linspace(0, h, n_options + 1).astype(int)
        white_scores = []
        for i in range(n_options):
            ys, ye = bands[i], bands[i + 1]
            band = white_mask[ys:ye, :]
            white_scores.append(np.count_nonzero(band) / band.size)
        return int(np.argmax(white_scores))

    @staticmethod
    def detect_item(frame: Frame) -> (str, str):
        item_name = pytesseract.image_to_string(ITEM_NAME_FRAME_PROCESSOR.prepare_frame(frame), config='--psm 7')
        item_quantity = pytesseract.image_to_string(ITEM_QUANTITY_FRAME_PROCESSOR.prepare_frame(frame),
                                                    config='--psm 7 tessedit_char_whitelist=0123456789')
        return item_name, item_quantity

    @staticmethod
    def detect_quantity_to_sell(frame: Frame) -> str:
        frame = QUANTITY_TO_SELL_FRAME_PROCESSOR.prepare_frame(frame)
        return pytesseract.image_to_string(frame, config='--psm 7 tessedit_char_whitelist=0123456789')

    # # Small cleanups (optional, but helps on video)
    # k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    # frame = cv2.morphologyEx(frame, cv2.MORPH_OPEN, k)
    # frame = cv2.morphologyEx(frame, cv2.MORPH_CLOSE, k)

    # return text, quantity
    pass
