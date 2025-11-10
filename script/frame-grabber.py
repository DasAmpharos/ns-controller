import argparse
import os.path

import click
import cv2


@click.command()
@click.option('--source', type=int, default=0)
@click.option('--width', type=int, default=1280)
@click.option('--height', type=int, default=720)
@click.option('--fps', type=int, default=60)
@click.option('-d', '--directory', default='frames')
def main(source: int, width: int, height: int, fps: int, directory: str) -> None:
    video_capture = cv2.VideoCapture(source)
    video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG'))
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    video_capture.set(cv2.CAP_PROP_FPS, fps)

    frames = 0
    while True:
        success, frame = video_capture.read()
        if not success:
            raise ValueError('Error occurred while getting frame')

        cv2.imshow('Capture Frame', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            filepath = os.path.join(directory, f'frame-{frames}.jpg')
            filepath = os.path.abspath(filepath)
            dirname = os.path.dirname(filepath)
            os.makedirs(dirname, exist_ok=True)
            cv2.imwrite(filepath, frame)
            frames += 1
            continue
        if key == ord('q'):
            break
    video_capture.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()