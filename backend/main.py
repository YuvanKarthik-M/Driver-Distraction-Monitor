import asyncio
import json
import time

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
from detectors.face_detector import FaceDetector
from detectors.hand_detector import HandDetector
from detectors.phone_detector import PhoneDetector

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def new_state():
    return {"calib": [], "calib_start": None, "base": (0.0, 0.0), "ready": False,
            "closed_since": None, "away_since": None,
            "phone_seen": None, "phone_since": None,
            "hand_seen": None, "hand_since": None, "frames": 0}


def held_for(s, name, observed, now, hold, need):
    """True once `name` has been present for `need` seconds.

    `observed` is True/False for a frame where detection ran, None when it was skipped.
    Something seen at any point in the last `hold` seconds counts as present, so a detector
    that only catches it now and then does not keep resetting the timer.
    """
    if observed:
        s[name + "_seen"] = now
    seen = s[name + "_seen"] is not None and now - s[name + "_seen"] <= hold
    s[name + "_since"] = (s[name + "_since"] or now) if seen else None
    return bool(s[name + "_since"]) and now - s[name + "_since"] > need


def analyse(r, s, phone_obs=None, hand_obs=None):
    now = time.time()
    phone = held_for(s, "phone", phone_obs, now, config.PHONE_HOLD_SECONDS, config.PHONE_SECONDS)
    hand = held_for(s, "hand", hand_obs, now, config.HAND_HOLD_SECONDS, config.HAND_SECONDS)
    phone = phone or (config.HAND_EAR_ENABLED and hand)  # visible phone, or hand held at the ear

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
    hand_det = None
    if config.HAND_EAR_ENABLED:
        try:
            hand_det = HandDetector(config.HAND_EAR_DISTANCE)
        except Exception as e:
            print("Hand-at-ear detection disabled:", e)
    state = new_state()

    def work(frame, run_detect):
        face = detector.process(frame)
        phone_obs = phone_det.detect(frame) if (phone_det and run_detect) else None
        hand_obs = None
        if hand_det and run_detect and face is not None:
            hand_obs = hand_det.near_face_side(frame, face["geo"])
        return face, phone_obs, hand_obs

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
            face, phone_obs, hand_obs = await asyncio.get_running_loop().run_in_executor(
                None, work, frame, run_phone)
            await websocket.send_text(json.dumps(analyse(face, state, phone_obs, hand_obs)))
    except WebSocketDisconnect:
        pass
    finally:
        detector.close()
        if phone_det:
            phone_det.close()
        if hand_det:
            hand_det.close()