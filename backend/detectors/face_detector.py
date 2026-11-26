import os
import urllib.request

import math

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "face_landmarker.task")

RIGHT_EYE = [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]


def _ear(pts):
    a = np.linalg.norm(pts[1] - pts[5])
    b = np.linalg.norm(pts[2] - pts[4])
    c = np.linalg.norm(pts[0] - pts[3])
    return (a + b) / (2.0 * c)


def _ensure_model():
    path = os.path.abspath(MODEL_PATH)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print("Downloading face_landmarker.task (one time, ~4 MB)...")
        urllib.request.urlretrieve(MODEL_URL, path)
    return path


class FaceDetector:
    def __init__(self):
        options = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_ensure_model()),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(options)
        self.smooth = None  # (yaw, pitch) smoothed over frames

    def process(self, frame):
        """Returns dict(yaw, pitch, ear) or None if no face."""
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self.landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if not res.face_landmarks:
            return None
        lm = res.face_landmarks[0]
        xy = lambda i: np.array([lm[i].x * w, lm[i].y * h])

        ear = (_ear(np.array([xy(i) for i in RIGHT_EYE])) +
               _ear(np.array([xy(i) for i in LEFT_EYE]))) / 2.0

        # Yaw: where the nose sits between the left and right edge of the face.
        # Stable and never flips sign: one direction is +, the other is -.
        nose_x = lm[1].x
        left = abs(nose_x - lm[234].x)
        right = abs(lm[454].x - nose_x)
        r = (right - left) / max(left + right, 1e-6)
        yaw = math.degrees(math.asin(max(-1.0, min(1.0, r))))

        # Pitch: where the nose sits between the eye line and the chin.
        # Approximate scale; the calibration step removes your personal offset.
        eye_y = (lm[33].y + lm[263].y) / 2
        p = (lm[1].y - eye_y) / max(lm[152].y - eye_y, 1e-6)
        pitch = p * 200.0

        # Smooth over frames to remove jitter.
        if self.smooth is None:
            self.smooth = (yaw, pitch)
        else:
            a = 0.4
            self.smooth = (a * yaw + (1 - a) * self.smooth[0],
                           a * pitch + (1 - a) * self.smooth[1])
        yaw, pitch = self.smooth
        # Face geometry in pixels, used to check whether a hand is beside the face.
        left, right = xy(234), xy(454)
        geo = {
            "edges": [tuple(left), tuple(right)],
            "width": float(np.linalg.norm(left - right)),
            "eye_y": float((xy(33)[1] + xy(263)[1]) / 2),
            "chin_y": float(xy(152)[1]),
        }
        return {"yaw": float(yaw), "pitch": float(pitch), "ear": float(ear), "geo": geo}

    def close(self):
        self.landmarker.close()