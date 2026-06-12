"""
hand_gestures.py

Standalone OpenCV hand gesture recognizer adapted from:
https://github.com/cesar-cipher/Python-Hand-Gesture-Recognition

Recognizes:
    Waving
    Rock      (0 fingers)
    Pointing  (1 finger)
    Scissors  (2 fingers)
    Open hand (4-5 fingers)

Requirements:
    pip install opencv-python numpy

Run:
    python hand_gestures.py

Controls:
    q  quit
    r  recalibrate the background
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field

import cv2
import numpy as np


CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

CALIBRATION_FRAMES = 30
BACKGROUND_WEIGHT = 0.5
OBJECT_THRESHOLD = 18
GESTURE_HISTORY = 12
WAVE_CHECK_INTERVAL = 8
WAVE_MIN_DELTA = 18

ROI_TOP = 40
ROI_BOTTOM = 360
ROI_LEFT = 300
ROI_RIGHT = 620

MIN_HAND_AREA = 2_500
BOX_COLOR = (0, 255, 0)
TEXT_COLOR = (255, 255, 255)
TEXT_SHADOW = (0, 0, 0)
ROI_COLOR = (255, 255, 255)


@dataclass
class HandData:
    top: tuple[int, int]
    bottom: tuple[int, int]
    left: tuple[int, int]
    right: tuple[int, int]
    center_x: int
    previous_center_x: int = 0
    is_in_frame: bool = True
    is_waving: bool = False
    fingers: int = 0
    gesture_history: deque[int] = field(default_factory=lambda: deque(maxlen=GESTURE_HISTORY))

    def update(
        self,
        top: tuple[int, int],
        bottom: tuple[int, int],
        left: tuple[int, int],
        right: tuple[int, int],
    ) -> None:
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
        self.center_x = int((left[0] + right[0]) / 2)
        self.is_in_frame = True

    def check_for_waving(self, center_x: int) -> None:
        self.previous_center_x = self.center_x
        self.center_x = center_x
        self.is_waving = abs(self.center_x - self.previous_center_x) >= WAVE_MIN_DELTA

    def update_fingers(self, finger_count: int) -> None:
        self.gesture_history.append(finger_count)
        if len(self.gesture_history) == self.gesture_history.maxlen:
            self.fingers = Counter(self.gesture_history).most_common(1)[0][0]


background: np.ndarray | None = None
hand: HandData | None = None
frames_elapsed = 0


def get_region(frame: np.ndarray) -> np.ndarray:
    """Crop and prepare the hand ROI for background subtraction."""
    region = frame[ROI_TOP:ROI_BOTTOM, ROI_LEFT:ROI_RIGHT]
    region = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(region, (5, 5), 0)


def update_background(region: np.ndarray) -> None:
    """Build a running average of the empty ROI during calibration."""
    global background

    if background is None:
        background = region.copy().astype("float")
        return

    cv2.accumulateWeighted(region, background, BACKGROUND_WEIGHT)


def segment_hand(region: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """Return the threshold image and largest foreground contour in the ROI."""
    global hand

    if background is None:
        return None

    diff = cv2.absdiff(background.astype(np.uint8), region)
    threshold = cv2.threshold(diff, OBJECT_THRESHOLD, 255, cv2.THRESH_BINARY)[1]

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel, iterations=1)
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [contour for contour in contours if cv2.contourArea(contour) >= MIN_HAND_AREA]

    if not contours:
        if hand is not None:
            hand.is_in_frame = False
            hand.is_waving = False
        return None

    return threshold, max(contours, key=cv2.contourArea)


def update_hand_data(threshold: np.ndarray, contour: np.ndarray) -> None:
    """Update hand bounds, waving state, and smoothed finger count."""
    global hand

    hull = cv2.convexHull(contour)
    top = tuple(hull[hull[:, :, 1].argmin()][0])
    bottom = tuple(hull[hull[:, :, 1].argmax()][0])
    left = tuple(hull[hull[:, :, 0].argmin()][0])
    right = tuple(hull[hull[:, :, 0].argmax()][0])
    center_x = int((left[0] + right[0]) / 2)

    if hand is None:
        hand = HandData(top=top, bottom=bottom, left=left, right=right, center_x=center_x)
    else:
        hand.update(top, bottom, left, right)

    if frames_elapsed % WAVE_CHECK_INTERVAL == 0:
        hand.check_for_waving(center_x)

    hand.update_fingers(count_fingers(threshold))


def count_fingers(threshold: np.ndarray) -> int:
    """Estimate raised fingers by counting hand intersections near the fingertips."""
    if hand is None:
        return 0

    hand_height = hand.bottom[1] - hand.top[1]
    hand_width = hand.right[0] - hand.left[0]
    if hand_height <= 0 or hand_width <= 0:
        return 0

    line_height = int(hand.top[1] + 0.2 * hand_height)
    line_height = max(0, min(line_height, threshold.shape[0] - 1))

    line_mask = np.zeros(threshold.shape[:2], dtype=np.uint8)
    cv2.line(line_mask, (0, line_height), (threshold.shape[1], line_height), 255, 1)
    intersections = cv2.bitwise_and(threshold, threshold, mask=line_mask)

    contours, _ = cv2.findContours(intersections.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    fingers = 0
    max_finger_width = 0.75 * hand_width
    for contour in contours:
        _, _, width, _ = cv2.boundingRect(contour)
        if 5 < width < max_finger_width:
            fingers += 1

    return min(fingers, 5)


def current_gesture() -> str:
    if frames_elapsed < CALIBRATION_FRAMES:
        return "Calibrating..."
    if hand is None or not hand.is_in_frame:
        return "No hand detected"
    if hand.is_waving:
        return "Waving"
    if hand.fingers == 0:
        return "Fist"
    if hand.fingers == 1:
        return "Pointing"
    if hand.fingers == 2:
        return "Scissor"
    if hand.fingers >= 4:
        return "Open hand"
    return f"{hand.fingers} fingers"


def draw_text(frame: np.ndarray, text: str, x: int = 12, y: int = 36) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.0
    thickness = 3
    cv2.putText(frame, text, (x, y), font, scale, TEXT_SHADOW, thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), font, scale, TEXT_COLOR, thickness, cv2.LINE_AA)


def draw_hand_box(frame: np.ndarray, contour: np.ndarray) -> None:
    x, y, width, height = cv2.boundingRect(contour)
    top_left = (ROI_LEFT + x, ROI_TOP + y)
    bottom_right = (ROI_LEFT + x + width, ROI_TOP + y + height)
    cv2.rectangle(frame, top_left, bottom_right, BOX_COLOR, 3)


def reset_calibration() -> None:
    global background, hand, frames_elapsed
    background = None
    hand = None
    frames_elapsed = 0


def main() -> int:
    global frames_elapsed

    capture = cv2.VideoCapture(CAMERA_INDEX)
    if not capture.isOpened():
        print("Could not open the laptop camera.")
        return 1

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    print("Keep your hand out of the white box while it calibrates.")
    print("Then put your hand inside the box. q = quit, r = recalibrate.")

    while True:
        ok, frame = capture.read()
        if not ok:
            print("Could not read from the camera.")
            break

        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        frame = cv2.flip(frame, 1)
        region = get_region(frame)

        if frames_elapsed < CALIBRATION_FRAMES:
            update_background(region)
        else:
            segmented = segment_hand(region)
            if segmented is not None:
                threshold, contour = segmented
                update_hand_data(threshold, contour)
                draw_hand_box(frame, contour)
                cv2.imshow("Segmented Hand", threshold)

        cv2.rectangle(frame, (ROI_LEFT, ROI_TOP), (ROI_RIGHT, ROI_BOTTOM), ROI_COLOR, 2)
        draw_text(frame, current_gesture())
        cv2.imshow("Hand Gesture Recognition - q to quit", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("r"):
            reset_calibration()
            continue

        frames_elapsed += 1

    capture.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
