import math
import os
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "hand_landmarker.task")


def _ensure_model():
    path = os.path.abspath(MODEL_PATH)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print("Downloading hand_landmarker.task (one time, ~8 MB)...")
        urllib.request.urlretrieve(MODEL_URL, path)
    return path


def hand_beside_face(hand_points, geo, w, h, factor):
    """True if the centre of the hand is beside the face, near either cheek/ear edge.

    hand_points: list of landmarks with normalised x, y.
    geo: face geometry in pixels (edges, width, eye_y, chin_y).
    factor: allowed distance, in face widths.
    """
    cx = sum(p.x for p in hand_points) / len(hand_points) * w
    cy = sum(p.y for p in hand_points) / len(hand_points) * h
    fw = geo["width"]
    if not (geo["eye_y"] - 0.6 * fw <= cy <= geo["chin_y"]):  # between brow level and chin
        return False
    return any(math.hypot(cx - ex, cy - ey) < factor * fw for ex, ey in geo["edges"])


class HandDetector:
    """Spots a hand held beside the face, which is how a phone is held to the ear.

    A phone held sideways is almost invisible to an object detector, so this is used as a
    second signal for a phone call.
    """

    def __init__(self, distance_factor=0.6):
        self.factor = distance_factor
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_ensure_model()),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=2,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def near_face_side(self, frame, geo):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        return any(hand_beside_face(hand, geo, w, h, self.factor) for hand in res.hand_landmarks)

    def close(self):
        self.landmarker.close()