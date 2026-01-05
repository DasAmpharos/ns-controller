import argparse
import os.path
import time
from datetime import datetime

import click
import cv2


@click.command()
@click.option('--source', type=int, default=0)
@click.option('--width', type=int, default=1280)
@click.option('--height', type=int, default=720)
@click.option('--fps', type=int, default=60)
@click.option('-d', '--directory', default='frames')
def main(source: str | int, width: int, height: int, fps: int, directory: str) -> None:
    video_capture = cv2.VideoCapture(source)
    video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG'))
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    video_capture.set(cv2.CAP_PROP_FPS, fps)

    time.sleep(3.0) # Wait for camera to stabilize

    while True:
        success, frame = video_capture.read()
        if not success:
            continue

        now = datetime.now()
        timestamp = now.strftime('%Y%m%d%H%M%S')
        filepath = os.path.join(directory, f'{timestamp}.jpg')
        filepath = os.path.abspath(filepath)
        dirname = os.path.dirname(filepath)
        os.makedirs(dirname, exist_ok=True)
        cv2.imwrite(filepath, frame)
        break

    video_capture.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()