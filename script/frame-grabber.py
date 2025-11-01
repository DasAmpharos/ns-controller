import argparse
import os.path

import cv2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--directory', default='frames')
    args = parser.parse_args()

    source = 0
    video_capture = cv2.VideoCapture(source)
    video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc(*'MJPG'))
    video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    video_capture.set(cv2.CAP_PROP_FPS, 30)

    frames = 0
    while True:
        success, frame = video_capture.read()
        if not success:
            raise ValueError('Error occurred while getting frame')

        cv2.imshow('Capture Frame', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            filepath = os.path.join(args.directory, f'frame-{frames}.jpg')
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