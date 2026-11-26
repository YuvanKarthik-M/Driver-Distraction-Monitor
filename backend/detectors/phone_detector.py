import os
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/object_detector/"
             "efficientdet_lite0/float32/1/efficientdet_lite0.tflite")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "efficientdet_lite0.tflite")


def _ensure_model():
    path = os.path.abspath(MODEL_PATH)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print("Downloading efficientdet_lite0.tflite (one time, ~14 MB)...")
        urllib.request.urlretrieve(MODEL_URL, path)
    return path


class PhoneDetector:
    """Looks for a 'cell phone' (a COCO class) in the frame."""

    def __init__(self, confidence=0.4):
        options = vision.ObjectDetectorOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_ensure_model()),
            running_mode=vision.RunningMode.IMAGE,
            score_threshold=confidence,
            category_allowlist=["cell phone"],
            max_results=3,
        )
        self.detector = vision.ObjectDetector.create_from_options(options)

    def detect(self, frame):
        """True if a phone is visible in this BGR frame."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        return len(result.detections) > 0

    def close(self):
        self.detector.close()