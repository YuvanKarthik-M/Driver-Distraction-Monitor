import asyncio
import json
import time

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
from detectors.face_detector import FaceDetector

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def new_state():
    return {"calib": [], "calib_start": None, "base": (0.0, 0.0), "ready": False,
            "closed_since": None, "away_since": None}


def analyse(r, s):
    now = time.time()

    if r is None:  # no face in frame counts as looking away
        s["closed_since"] = None
        s["away_since"] = s["away_since"] or now
        away = now - s["away_since"] > config.AWAY_SECONDS
        return {"face": False, "calibrating": not s["ready"], "yaw": 0, "pitch": 0, "ear": 0,
                "status": "looking_away" if (away and s["ready"]) else "ok"}

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

    status = "ok"
    if s["away_since"] and now - s["away_since"] > config.AWAY_SECONDS:
        status = "looking_away"
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
    state = new_state()
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
            # Run the heavy detection in a worker thread so the server stays responsive.
            result = await asyncio.get_running_loop().run_in_executor(None, detector.process, frame)
            await websocket.send_text(json.dumps(analyse(result, state)))
    except WebSocketDisconnect:
        pass
    finally:
        detector.close()