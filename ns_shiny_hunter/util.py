from collections import deque

import cv2
import numpy as np

from ns_shiny_hunter.frame import Frame


def get_brightness(frame: Frame) -> float:
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame.mean()


def is_outlier(value: float,
               values: list[float],
               lower_percentile: int = 1,
               upper_percentile: int = 99) -> bool:
    p1 = np.percentile(values, lower_percentile)
    p2 = np.percentile(values, upper_percentile)
    iqr = p2 - p1

    upper_bound = p2 + 1.5 * iqr
    return value > upper_bound
