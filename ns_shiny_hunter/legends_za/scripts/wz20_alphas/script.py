import time

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.frames import LegendsZAReferenceFrames
from .frames import ReferenceFrames
from .state import State


class WildZone20Alphas:
    def __init__(self, frame_grabber: FrameGrabber, controller: NsControllerClient, resets: int = 1):
        self.frame_grabber = frame_grabber
        self.controller = controller
        self.state = State.OVERWORLD
        self.resets = resets

    def run(self):
        try:
            while True:
                match self.state:
                    case State.OVERWORLD:
                        # run up to spawn all alphas
                        start = time.time()
                        self.controller.set_stick(ls_y=1, post_delay=0.25)
                        self.controller.click([Button.B], down=0.1, post_delay=0.1)
                        time.sleep(2.25 - (time.time() - start))
                        self.controller.clear(post_delay=0.1)
                        # run back to bench
                        start = time.time()
                        self.controller.set_stick(ls_y=-1, post_delay=0.25)
                        self.controller.click([Button.B], down=0.1, post_delay=0.1)
                        time.sleep(2.5 - (time.time() - start))
                        self.controller.clear(post_delay=0.1)
                        # interact with bench
                        self.controller.click([Button.A], down=0.1, post_delay=1)
                        if ReferenceFrames.WHAT_A_NICE_BENCH.matches(self.frame_grabber.frame):
                            self.state = State.WHAT_A_NICE_BENCH
                    case State.WHAT_A_NICE_BENCH:
                        self.controller.click([Button.A], down=0.1, post_delay=0.1)
                        if ReferenceFrames.HANG_OUT_HERE.matches(self.frame_grabber.frame):
                            self.state = State.HANG_OUT_HERE
                    case State.HANG_OUT_HERE:
                        self.controller.click([Button.A], down=0.1, post_delay=0.1)
                        if LegendsZAReferenceFrames.OVERWORLD.matches(self.frame_grabber.frame):
                            self.resets += 1
                            print(f"Reset #{self.resets}...")
                            self.state = State.OVERWORLD

                # if BenchResetReferenceFrames.YES_NO_CONFIRMATION.matches(frame):
                #     self.controller.click([Button.A], down=0.1, post_delay=0.1)
                #     time.sleep(12.5)
                #     resets += 1
                #     print(f"Reset #{resets}...")
                # elif BenchResetReferenceFrames.OVERWORLD.matches(frame):
                #     self.controller.set_stick(ls_y=-1, post_delay=0.1)
                #     self.controller.clear(post_delay=0.5)
                #     self.controller.click([Button.A], down=0.1, post_delay=0.1)
                # elif BenchResetReferenceFrames.WHAT_A_NICE_BENCH.matches(frame):
                #     self.controller.click([Button.A], down=0.1, post_delay=0.1)
                # elif BenchResetReferenceFrames.HANG_OUT_HERE.matches(frame):
                #     self.controller.click([Button.A], down=0.1, post_delay=0.1)
                # time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\nExiting BenchReset after {self.resets} resets...")
