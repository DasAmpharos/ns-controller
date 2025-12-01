import time
from typing import Final

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames
from .state import State


class FlyReset:
    WILD_ZONE_4: Final = (1.0, 0.0, 0.1)
    WILD_ZONE_10: Final = (0.9, 0.438, 0.1)
    WILD_ZONE_17: Final = (0.514, 0.857, 0.1)
    SHUTTERBUG_CAFE: Final = (0.25, -0.25, 0.05)
    RESEARCH_LAB: Final = (0, -1, 0.05)

    def __init__(self,
                 action: tuple[float, float, float],
                 frame_grabber: FrameGrabber,
                 controller: NsControllerClient,
                 state: State = State.OVERWORLD,
                 resets: int = 1):
        self.action = action
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.state = state
        self.resets = resets

    def run(self):
        try:
            while True:
                match self.state:
                    case State.OVERWORLD:
                        self.resets += 1
                        print('State.OVERWORLD')
                        print(f'Reset #{self.resets}...')
                        self.controller.click(Button.PLUS, post_delay=1)
                        while not LegendsZAReferenceFrames.OPEN_MAP.matches(self.frame_grabber.frame):
                            time.sleep(0.1)
                        self.state = State.OPEN_MAP
                    case State.OPEN_MAP:
                        print('State.OPEN_MAP')
                        self.controller.set_stick(ls_x=self.action[0], ls_y=self.action[1], post_delay=self.action[2])
                        self.controller.clear(post_delay=1)
                        while not LegendsZAReferenceFrames.TRAVEL_HERE.matches(self.frame_grabber.frame):
                            time.sleep(0.1)
                        self.state = State.TRAVEL_HERE
                    case State.TRAVEL_HERE:
                        print('State.TRAVEL_HERE')
                        while not LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                            self.controller.click(Button.A)
                        self.state = State.OVERWORLD
        except KeyboardInterrupt:
            print(f"\nExiting FlyReset after {self.resets} resets...")
