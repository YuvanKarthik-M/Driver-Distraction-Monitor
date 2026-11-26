import asyncio
import json
import time

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
from detectors.face_detector import FaceDetector
from detectors.phone_detector import PhoneDetector

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def new_state():
    return {"calib": [], "calib_start": None, "base": (0.0, 0.0), "ready": False,
            "closed_since": None, "away_since": None,
            "phone_last_seen": None, "phone_since": None, "frames": 0}


def phone_active(s, phone_obs, now):
    """phone_obs: True/False for a frame where detection ran, None when it was skipped.

    A phone counts as present if it was seen at any point in the last PHONE_HOLD_SECONDS,
    so a phone that the detector only catches now and then (for example near the ear)
    does not keep resetting the timer.
    """
    if phone_obs:
        s["phone_last_seen"] = now
    seen = s["phone_last_seen"] is not None and now - s["phone_last_seen"] <= config.PHONE_HOLD_SECONDS
    s["phone_since"] = (s["phone_since"] or now) if seen else None
    return bool(s["phone_since"]) and now - s["phone_since"] > config.PHONE_SECONDS


def analyse(r, s, phone_obs=None):
    now = time.time()
    phone = phone_active(s, phone_obs, now)

    if r is None:  # no face in frame counts as looking away
        s["closed_since"] = None
        s["away_since"] = s["away_since"] or now
        away = now - s["away_since"] > config.AWAY_SECONDS
        status = "ok"
        if s["ready"]:
            status = "phone" if phone else ("looking_away" if away else "ok")
        return {"face": False, "calibrating": not s["ready"], "yaw": 0, "pitch": 0, "ear": 0,
                "status": status}

    if not s["ready"]:
        if s["calib_start"] is None:
            s["calib_start"] = now
        s["calib"].append((r["yaw"], r["pitch"]))
        if (now - s["calib_start"] >= config.CALIBRATION_SECONDS
                and len(s["calib"]) >= config.CALIBRATION_MIN_FRAMES):
            s["base"] = tuple(np.mean(s["calib"], axis=0))
            s["ready"] = True
        return {"face": True, "calibrating": True, "yaw": 0, "pitch": 0,
                "ear": round(r["ear"], 3), "status": "ok"}

    yaw = r["yaw"] - s["base"][0]
    pitch = r["pitch"] - s["base"][1]
    away_now = abs(yaw) > config.YAW_LIMIT or abs(pitch) > config.PITCH_LIMIT
    closed_now = r["ear"] < config.EAR_THRESHOLD

    s["away_since"] = (s["away_since"] or now) if away_now else None
    s["closed_since"] = (s["closed_since"] or now) if closed_now else None

    # Priority: eyes closed > phone > looking away
    status = "ok"
    if s["away_since"] and now - s["away_since"] > config.AWAY_SECONDS:
        status = "looking_away"
    if phone:
        status = "phone"
    if s["closed_since"] and now - s["closed_since"] > config.CLOSED_SECONDS:
        status = "drowsy"

    return {"face": True, "calibrating": False, "yaw": round(yaw, 1),
            "pitch": round(pitch, 1), "ear": round(r["ear"], 3), "status": status}


@app.get("/")
def health():
    return {"status": "ok"}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    detector = FaceDetector()
    phone_det = None
    try:
        phone_det = PhoneDetector(config.PHONE_CONFIDENCE)
    except Exception as e:  # the app still works without phone detection
        print("Phone detection disabled:", e)
    state = new_state()

    def work(frame, run_phone):
        face = detector.process(frame)
        phone_obs = phone_det.detect(frame) if (phone_det and run_phone) else None
        return face, phone_obs

    try:
        while True:
            msg = await websocket.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("text") == "recalibrate":
                state = new_state()
                detector.smooth = None
                continue
            data = msg.get("bytes")
            if not data:
                continue
            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                continue
            run_phone = state["frames"] % config.PHONE_EVERY_N_FRAMES == 0
            state["frames"] += 1
            # Run the heavy detection in a worker thread so the server stays responsive.
            face, phone_obs = await asyncio.get_running_loop().run_in_executor(
                None, work, frame, run_phone)
            await websocket.send_text(json.dumps(analyse(face, state, phone_obs)))
    except WebSocketDisconnect:
        pass
    finally:
        detector.close()
        if phone_det:
            phone_det.close()