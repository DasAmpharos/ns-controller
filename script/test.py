import time

import cv2
import numpy as np
import pytesseract

from ns_controller.client import NsControllerClient
from ns_controller.pb.ns_controller_pb2 import Button, ControllerState
from ns_shiny_hunter.frame_grabber import FrameGrabber
from ns_shiny_hunter.legends_za.scripts.sushi_high_roller.frames import DIALOG_FRAME_PROCESSOR, \
    POKEMON_CENTER_DIALOG_OPTIONS_FRAME_PROCESSOR
from ns_shiny_hunter.legends_za.scripts.sushi_high_roller.script import SushiHighRoller
from ns_shiny_hunter.legends_za.scripts.sushi_high_roller.state import State


def main():
    # client = NsControllerClient('10.117.1.143', 50051)
    # pair_controller(client)
    # try:
    #     with FrameGrabber(0, imshow=False) as frame_grabber:
    #         script = SushiHighRoller(frame_grabber, client, state=State.POKEMON_CENTER_DIALOG)
    #         script.run()
    # except KeyboardInterrupt:
    #     print("Exiting...")

    try:
        with FrameGrabber(0, imshow=False) as frame_grabber:
            time.sleep(3)
            while True:
                frames = SushiHighRoller.detect_item(frame_grabber.frame)
                cv2.imshow("frame1", frames[0])
                cv2.imshow("frame2", frames[1])
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                time.sleep(0.1)
    except KeyboardInterrupt:
        cv2.destroyAllWindows()
        pass

        # script = SushiHighRoller(frame_grabber, client)
        # script.state_handler_a_to_talk_pokemon_center()
    # open_controller_menu(client)
    # client.set_stick(ls_y=1, post_delay=0.5)
    # client.click([Button.B])
    # time.sleep(3)
    # open_controller_menu(client)
    # client.clear()

def pair_controller(client: NsControllerClient):
    client.click([Button.L, Button.R], down=0.5, post_delay=0.1)
    client.click([Button.HOME], down=0.1, post_delay=3)
    client.click([Button.A], down=0.1, post_delay=3)

def open_controller_menu(client: NsControllerClient):
    client.clear(post_delay=0.1)
    client.click([Button.HOME], post_delay=1)
    client.click([Button.DPAD_DOWN], post_delay=0.5)
    for _ in range(6):
        client.click(buttons=[Button.DPAD_RIGHT], post_delay=0.05)
    client.click([Button.A], post_delay=1)
    client.click([Button.A])

if __name__ == '__main__':
    main()