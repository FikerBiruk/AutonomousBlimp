"""
webcam_gesture_detect.py

Real-time facial tracking, hand-presence detection, and an "anger meter"
driven by facial expression analysis - all from the laptop's built-in
webcam.

Labels
------
    * Hand visible anywhere in the frame   -> "STOP"
    * Otherwise (just the face)            -> "COME OVER"

Anger meter
-----------
For every tracked face the script also draws a horizontal bar at the
top of the frame and a per-face bar above each face. The meter is a
rough geometric estimate of "anger" on a 1-100 scale that combines:

    * Mouth aspect ratio (MAR) - how open/compressed the mouth is.
      An angry expression tends to press the lips together, so a small
      mouth opening pushes the meter up.
    * Mouth-to-face-width ratio - small => pursed lips => angrier.
    * Face squareness (face_height / face_width) - angry faces often
      look slightly wider / squarer than relaxed ones.

It is NOT a real ML emotion classifier (no model download required),
but it's a fun, dependency-free proxy that responds to obvious
changes in mouth shape.

Pipeline per frame:
    1.  Grab a frame from the laptop camera (VideoCapture(0)).
    2.  Detect all faces with the frontal-face Haar cascade.
    3.  Estimate the anger score for each face.
    4.  Build a YCrCb skin-colour mask and reject blobs inside any
        face box (so a hand near the face is still detected).
    5.  If a non-face skin blob exists, the label is "STOP", else
        "COME OVER".
    6.  Draw the face box (blue), the hand box (green), the anger bar
        above each face, the big top anger meter for the largest face,
        and the big STOP / COME OVER label at the top of the frame.
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


def detect_faces(cascade, frame_gray):
    """Return all face bounding boxes (x, y, w, h) found in the frame."""
    return cascade.detectMultiScale(
        frame_gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )


def largest_face(faces):
    """Return the biggest face box, or None if no faces were detected."""
    if len(faces) == 0:
        return None
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


def find_hand_blob(mask: np.ndarray, face_boxes, min_area: int = 5000):
    """Return (bbox, contour) of the largest skin blob OUTSIDE all face
    boxes, or None if no such blob exists."""
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

        bad = False
        for box in face_boxes:
            if face_box_intersects(box, cx, cy):
                bad = True
                break
            if face_overlap_fraction(box, c) > 0.5:
                bad = True
                break
        if bad:
            continue
        candidates.append(c)

    if not candidates:
        return None
    biggest = max(candidates, key=cv2.contourArea)
    return cv2.boundingRect(biggest), biggest


# ---------------------------------------------------------------------------
# Anger estimation (geometry, no ML model needed)
# ---------------------------------------------------------------------------
def estimate_mouth_box(face_bgr: np.ndarray):
    """Find the mouth region inside a face ROI.

    The mouth is approximated as the darkest compact region in the
    LOWER 40 % of the face.  Returns (x, y, w, h) in the FACE-ROI
    coordinate system, or None.
    """
    h, w = face_bgr.shape[:2]
    if h < 20 or w < 20:
        return None

    y0 = int(h * 0.55)
    roi = face_bgr[y0:h, :]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, th = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    central = th[:, int(w * 0.20):int(w * 0.80)]

    contours, _ = cv2.findContours(
        central, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None

    biggest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(biggest) < 0.005 * w * h:
        return None

    bx, by, bw, bh = cv2.boundingRect(biggest)
    return (bx + int(w * 0.20), by + y0, bw, bh)


def compute_anger_score(face_bgr: np.ndarray, face_box) -> int:
    """Estimate anger for one face on a 1-100 scale (clamped)."""
    x, y, w, h = face_box
    if w <= 0 or h <= 0:
        return 1

    squareness = min(w, h) / max(w, h)
    s_sq = (squareness - 0.7) / 0.3
    s_sq = float(np.clip(s_sq, 0.0, 1.0))

    mouth = estimate_mouth_box(face_bgr)
    if mouth is None:
        s_mar = 0.0
        s_comp = 0.0
    else:
        _, _, mw, mh = mouth
        if mw == 0:
            s_mar = 0.0
            s_comp = 0.0
        else:
            mar = mh / float(mw)
            s_mar = float(np.clip(1.0 - (mar / 0.6), 0.0, 1.0))

            comp = mw / float(w)
            s_comp = float(np.clip(1.0 - (comp / 0.5), 0.0, 1.0))

    score01 = 0.50 * s_mar + 0.30 * s_comp + 0.20 * s_sq
    score01 = float(np.clip(score01 ** 0.7, 0.0, 1.0))

    return max(1, int(round(1 + score01 * 99)))


# ---------------------------------------------------------------------------
# Temporal smoothing per face
# ---------------------------------------------------------------------------
class AngerSmoother:
    """EMA smoother so the anger meter doesn't jitter every frame."""

    def __init__(self, alpha: float = 0.35):
        self.alpha = alpha
        self.values: dict = {}

    def update(self, face_box, raw_score: int) -> int:
        key = tuple(face_box)
        prev = self.values.get(key, float(raw_score))
        smoothed = prev + self.alpha * (raw_score - prev)
        self.values[key] = smoothed
        return int(round(smoothed))

    def forget(self, keep_keys) -> None:
        self.values = {k: v for k, v in self.values.items() if k in keep_keys}


# ---------------------------------------------------------------------------
# On-screen drawing
# ---------------------------------------------------------------------------
def _anger_color(anger: int):
    if anger < 50:
        return (0, 200, 0)
    if anger < 80:
        return (0, 200, 255)
    return (0, 0, 255)


def draw_face_box(frame, face_box) -> None:
    if face_box is None:
        return
    x, y, w, h = face_box
    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 3)
    cv2.putText(
        frame, "Face",
        (x, max(0, y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2,
    )


def draw_mouth_box(frame, face_box, mouth_box) -> None:
    if face_box is None or mouth_box is None:
        return
    fx, fy, _, _ = face_box
    mx, my, mw, mh = mouth_box
    cv2.rectangle(
        frame,
        (fx + mx, fy + my),
        (fx + mx + mw, fy + my + mh),
        (0, 255, 255), 1,
    )


def draw_anger_meter_for_face(frame, face_box, anger: int) -> None:
    """Draw a small per-face anger bar above the face box."""
    if face_box is None:
        return
    x, y, w, h = face_box
    bar_w = max(60, w)
    bar_h = 8
    bx = x
    by = max(0, y - 22)

    cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (60, 60, 60), -1)
    fill_w = int(bar_w * (anger / 100.0))
    cv2.rectangle(frame, (bx, by), (bx + fill_w, by + bar_h), _anger_color(anger), -1)
    cv2.putText(
        frame, f"Anger {anger}",
        (bx, max(0, by - 4)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1,
    )


def draw_main_anger_meter(frame, anger: int) -> None:
    """Big top-of-frame meter for the primary (largest) face."""
    h, w = frame.shape[:2]
    bar_w = 300
    bar_h = 18
    bx = (w - bar_w) // 2
    by = 90

    cv2.rectangle(frame, (bx - 2, by - 2), (bx + bar_w + 2, by + bar_h + 2),
                  (0, 0, 0), -1)
    cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (60, 60, 60), -1)
    fill_w = int(bar_w * (anger / 100.0))
    cv2.rectangle(frame, (bx, by), (bx + fill_w, by + bar_h), _anger_color(anger), -1)

    label = f"ANGER  {anger}/100"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.putText(
        frame, label,
        ((w - tw) // 2, by + bar_h + th + 6),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, _anger_color(anger), 2,
    )


def draw_hand(frame, hand_info) -> None:
    if hand_info is None:
        return
    (x, y, w, h), contour = hand_info
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
    cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
    cv2.putText(
        frame, "Hand",
        (x, max(0, y - 8)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2,
    )


def draw_main_label(frame, text: str, color) -> None:
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
        (0, 0, 0), -1,
    )
    cv2.putText(frame, text, (x, y), font, scale, color, thickness)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> None:
    face_cascade = load_face_cascade()
    smoother = AngerSmoother(alpha=0.35)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError(
            "Could not open the webcam. Make sure no other app is using it "
            "and that the OS has granted camera permission."
        )

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    window_name = "Face + Anger + Hand - press 'q' to quit"
    print(f"Webcam opened. {window_name}")
    print("  Hand visible   -> 'STOP'")
    print("  Otherwise      -> 'COME OVER'")
    print("  Anger meter (1-100) tracks the largest face.")

    candidate = "COME OVER"
    stable = "COME OVER"
    streak = 0
    STABLE_THRESHOLD = 3

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab a frame from the webcam.")
            break

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. Detect faces.
        face_boxes = detect_faces(face_cascade, gray)
        primary_face = largest_face(face_boxes)

        # 2. Per-face anger score.
        keep_keys = set()
        per_face_anger: dict = {}
        per_face_mouth: dict = {}
        for box in face_boxes:
            tb = tuple(box)
            keep_keys.add(tb)
            fx, fy, fw, fh = box
            face_roi = frame[fy:fy + fh, fx:fx + fw]
            if face_roi.size == 0:
                continue
            raw = compute_anger_score(face_roi, box)
            smooth = smoother.update(tb, raw)
            per_face_anger[tb] = smooth
            per_face_mouth[tb] = estimate_mouth_box(face_roi)
        smoother.forget(keep_keys)

        primary_anger = per_face_anger.get(tuple(primary_face), 1) if primary_face else 1

        # 3. Draw faces + per-face anger bars.
        for box in face_boxes:
            tb = tuple(box)
            draw_face_box(frame, box)
            if tb in per_face_anger:
                draw_anger_meter_for_face(frame, box, per_face_anger[tb])
            if tb in per_face_mouth:
                draw_mouth_box(frame, box, per_face_mouth[tb])

        # 4. Big top-of-frame anger meter for the primary face.
        if primary_face is not None:
            draw_main_anger_meter(frame, primary_anger)

        # 5. Hand detection (face-excluded).
        mask = skin_mask(frame)
        hand_info = find_hand_blob(mask, [tuple(b) for b in face_boxes])
        draw_hand(frame, hand_info)
        hand_visible = hand_info is not None

        # 6. Choose the main STOP / COME OVER label.
        new_label = "STOP" if hand_visible else "COME OVER"
        if new_label == candidate:
            streak += 1
        else:
            candidate = new_label
            streak = 0
        if streak >= STABLE_THRESHOLD:
            stable = candidate

        label_color = (0, 0, 255) if stable == "STOP" else (0, 255, 0)
        draw_main_label(frame, stable, color=label_color)

        # 7. Status bar.
        status = (
            f"Faces: {len(face_boxes)}  |  "
            f"Hand: {'YES' if hand_visible else 'no'}  |  "
            f"Anger: {primary_anger}/100  |  "
            f"Label: {stable}"
        )
        cv2.putText(
            frame, status,
            (10, frame.shape[0] - 15),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
        )

        cv2.imshow(window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Released webcam and closed windows.")


if __name__ == "__main__":
    main()
