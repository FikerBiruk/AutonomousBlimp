"""
webcam_gesture_detect.py

Real-time facial tracking + simple hand-presence detection from the
laptop's built-in webcam. The on-screen label follows this rule:

    * A HAND is visible anywhere in the frame  ->  "STOP"
    * Otherwise (just the face)               ->  "COME OVER"

Pipeline per frame:
    1.  Grab a frame from the laptop camera (VideoCapture(0)).
    2.  Detect the largest face with the frontal-face Haar cascade
        (this is the "facial tracking" - the blue box follows the
        user's face).
    3.  Build a YCrCb skin-colour mask and clean it with morphology.
    4.  Reject any skin blob whose centre is inside the face box
        (or that overlaps the face box by more than 50 %).
    5.  If any skin blob OUTSIDE the face remains, a hand is present.
    6.  Draw the face box (blue) and the hand blob's bounding box
        (green) on the frame, and display "STOP" or "COME OVER" as
        a big label at the top.
    7.  Press 'q' to quit.

No extra packages are required beyond opencv-python and numpy, which
are already installed in this project.

Run:
    py webcam_gesture_detect.py
"""

from __future__ import annotations

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Face detection / tracking
# ---------------------------------------------------------------------------
def load_face_cascade() -> cv2.CascadeClassifier:
    """Load OpenCV's pre-trained frontal-face Haar cascade."""
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        raise RuntimeError(
            f"Failed to load Haar cascade from: {cascade_path}\n"
            "Make sure opencv-python is installed correctly."
        )
    return cascade


def detect_largest_face(cascade, frame_gray):
    """Return the (x, y, w, h) of the largest face in the grayscale frame,
    or None if no face is found."""
    faces = cascade.detectMultiScale(
        frame_gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )
    if len(faces) == 0:
        return None
    # Biggest face = primary tracked subject.
    return tuple(max(faces, key=lambda b: b[2] * b[3]))


# ---------------------------------------------------------------------------
# Face-vs-hand helpers
# ---------------------------------------------------------------------------
def face_box_intersects(box, cx: int, cy: int) -> bool:
    x, y, w, h = box
    return x <= cx <= x + w and y <= cy <= y + h


def face_overlap_fraction(box, contour) -> float:
    fx, fy, fw, fh = box
    cx, cy, cw, ch = cv2.boundingRect(contour)
    ix1 = max(fx, cx)
    iy1 = max(fy, cy)
    ix2 = min(fx + fw, cx + cw)
    iy2 = min(fy + fh, cy + ch)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    return inter / (cw * ch) if (cw * ch) > 0 else 0.0


# ---------------------------------------------------------------------------
# Skin segmentation
# ---------------------------------------------------------------------------
SKIN_LOWER = np.array([0, 133, 77],  dtype=np.uint8)
SKIN_UPPER = np.array([255, 173, 127], dtype=np.uint8)


def skin_mask(frame_bgr: np.ndarray) -> np.ndarray:
    ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, SKIN_LOWER, SKIN_UPPER)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    return mask


def find_hand_blob(mask: np.ndarray, face_box, min_area: int = 5000):
    """Return (x, y, w, h) of the largest skin blob OUTSIDE the face box,
    or None if no such blob exists."""
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    candidates = []
    for c in contours:
        if cv2.contourArea(c) < min_area:
            continue
        m = cv2.moments(c)
        if m["m00"] == 0:
            continue
        cx = int(m["m10"] / m["m00"])
        cy = int(m["m01"] / m["m00"])

        if face_box is not None:
            if face_box_intersects(face_box, cx, cy):
                continue
            if face_overlap_fraction(face_box, c) > 0.5:
                continue

        candidates.append(c)

    if not candidates:
        return None
    biggest = max(candidates, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(biggest)
    return (x, y, w, h), biggest  # both the axis-aligned box and the contour


# ---------------------------------------------------------------------------
# On-screen drawing
# ---------------------------------------------------------------------------
def draw_face_box(frame, face_box) -> None:
    if face_box is None:
        return
    x, y, w, h = face_box
    # Thick blue rectangle that follows the face.
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 3)
    cv2.putText(
        frame,
        "Face (tracking)",
        (x, max(0, y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 0, 0),
        2,
    )


def draw_hand(frame, hand_info) -> None:
    if hand_info is None:
        return
    (x, y, w, h), contour = hand_info
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
    cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
    cv2.putText(
        frame,
        "Hand",
        (x, max(0, y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2,
    )


def draw_label(frame, text: str, color) -> None:
    if not text:
        return
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.6
    thickness = 4
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    x = (frame.shape[1] - tw) // 2
    y = 65
    cv2.rectangle(
        frame,
        (x - 20, y - th - 20),
        (x + tw + 20, y + 20),
        (0, 0, 0),
        -1,
    )
    cv2.putText(frame, text, (x, y), font, scale, color, thickness)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> None:
    face_cascade = load_face_cascade()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError(
            "Could not open the webcam. Make sure no other app is using it "
            "and that the OS has granted camera permission."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    window_name = "Face Tracking + Hand Detection - press 'q' to quit"
    print(f"Webcam opened. {window_name}")
    print("  Hand visible -> 'STOP'")
    print("  Otherwise    -> 'COME OVER'")

    # Temporal smoothing for the STOP / COME OVER label.
    candidate = "COME OVER"
    stable = "COME OVER"
    streak = 0
    STABLE_THRESHOLD = 3

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab a frame from the webcam.")
            break

        # Mirror the preview.
        frame = cv2.flip(frame, 1)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Facial tracking.
        face_box = detect_largest_face(face_cascade, gray)
        draw_face_box(frame, face_box)

        # 2. Skin mask + hand presence (face-excluded).
        mask = skin_mask(frame)
        hand_info = find_hand_blob(mask, face_box)
        draw_hand(frame, hand_info)

        hand_visible = hand_info is not None

        # 3. Decide the label.
        new_label = "STOP" if hand_visible else "COME OVER"
        if new_label == candidate:
            streak += 1
        else:
            candidate = new_label
            streak = 0
        if streak >= STABLE_THRESHOLD:
            stable = candidate

        # Red for STOP (more attention-grabbing), green for COME OVER.
        label_color = (0, 0, 255) if stable == "STOP" else (0, 255, 0)
        draw_label(frame, stable, color=label_color)

        # 4. Status bar.
        status = (
            f"Face: {'tracking' if face_box else 'no'}  |  "
            f"Hand: {'YES' if hand_visible else 'no'}  |  "
            f"Label: {stable}"
        )
        cv2.putText(
            frame,
            status,
            (10, frame.shape[0] - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
        )

        # 5. Debug inset: skin mask with face region blacked out.
        if face_box is not None:
            x, y, w, h = face_box
            cv2.rectangle(mask, (x, y), (x + w, y + h), 0, -1)
        mask_small = cv2.resize(mask, (160, 120))
        mask_color = cv2.cvtColor(mask_small, cv2.COLOR_GRAY2BGR)
        frame[10:130, frame.shape[1] - 170:frame.shape[1] - 10] = mask_color
        cv2.putText(
            frame,
            "hand mask",
            (frame.shape[1] - 165, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Released webcam and closed windows.")


if __name__ == "__main__":
    main()
