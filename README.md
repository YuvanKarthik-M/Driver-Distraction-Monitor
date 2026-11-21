# Driver Monitor

A web app that watches a driver's face through the webcam and raises an alarm when the driver looks away from the road or closes their eyes for too long. It runs in the browser, so anyone with a webcam can try it without installing anything.

**Live demo:** https://driver-monitor-brown.vercel.app/

## Features

- **Looking-away detection.** Detects head turns left/right and up/down, relative to the driver's own normal position.
- **Eye-closure (drowsiness) detection.** Uses the eye aspect ratio (EAR) to tell a long eye closure from a normal blink.
- **Calibration.** The first seconds of every session teach the system the driver's normal head position, so it works for different faces and camera angles. A **Recalibrate** button restarts it at any time.
- **Audible alarm.** A repeating beep while the driver is distracted. Closed eyes and looking away use different pitches.
- **Stop / Start.** Stopping turns the camera off completely and pauses all timing.
- **Session summary.** Monitored time, attentive time, distracted time (with percentages), count and duration of each event type, and the longest single distraction.
- **Event log.** A timestamped list of every distraction event in the session.
- **Auto-reconnect.** The page reconnects to the backend by itself if the connection drops.

## How it works

```
Browser (React)                          Server (FastAPI + MediaPipe)
┌──────────────────────┐   JPEG frame   ┌──────────────────────────────┐
│ Webcam (getUserMedia)│ ─────────────► │ Face landmarks (468+ points) │
│ ~10 frames/second    │   WebSocket    │ Eye aspect ratio (EAR)       │
│                      │                │ Head yaw / pitch             │
│ Status, alarm,       │ ◄───────────── │ Calibration + timers         │
│ summary, event log   │   JSON result  │ Status decision              │
└──────────────────────┘                └──────────────────────────────┘
```

1. The browser captures the webcam, shrinks each frame to 320×240 and sends it over a WebSocket. It sends the next frame only after the previous result has come back.
2. The backend finds the face landmarks with MediaPipe's FaceLandmarker.
3. **Eyes:** the eye aspect ratio is computed from six landmarks per eye. A value below the threshold means the eye is closed.
4. **Head turn (yaw):** measured from where the nose sits between the left and right edge of the face.
5. **Head tilt (pitch):** measured from where the nose sits between the eye line and the chin.
6. Yaw and pitch are smoothed over frames, and the calibrated "normal" position is subtracted.
7. A status is only raised after the condition lasts long enough (see the table below), so blinks and quick glances do not cause false alarms.
8. The backend returns a small JSON message (`yaw`, `pitch`, `ear`, `status`, `calibrating`), and the page shows it and plays the alarm.

## Tech stack

| Part | Technology |
|---|---|
| Frontend | React 18, Vite, Web Audio API |
| Backend | Python, FastAPI, Uvicorn, WebSockets |
| Computer vision | MediaPipe FaceLandmarker, OpenCV, NumPy |
| Hosting | Vercel (frontend), Render with Docker (backend) |

## Project structure

```
driver-monitor/
├── README.md
├── DEPLOY.md                    # Render + Vercel deployment settings
├── .gitignore
├── backend/
│   ├── main.py                  # FastAPI app, WebSocket endpoint, alert logic
│   ├── config.py                # all thresholds
│   ├── requirements.txt
│   ├── Dockerfile               # used for deployment on Render
│   ├── models/
│   │   └── face_landmarker.task # MediaPipe model (downloaded on first run)
│   └── detectors/
│       └── face_detector.py     # landmarks, EAR, head yaw/pitch
└── frontend/
    ├── package.json
    ├── index.html
    ├── vite.config.js
    ├── .env.example             # name of the backend address variable
    └── src/
        ├── main.jsx
        ├── App.jsx              # camera, WebSocket, session timing
        ├── StatusPanel.jsx      # live status and numbers
        ├── SessionSummary.jsx   # session totals
        ├── EventLog.jsx         # list of events
        ├── useAlarm.js          # alarm sound
        └── styles.css
```

## Run it locally

You need **Python 3.10 or newer**, **Node.js 18 or newer**, and a webcam.

**1. Backend** (terminal 1)

```
cd backend
python -m venv venv
venv\Scripts\activate            # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

On the first run the backend downloads the MediaPipe model (about 4 MB) into `backend/models/`, so you need an internet connection once. If the download fails, get `face_landmarker.task` from the MediaPipe model page and put it in that folder by hand.

**2. Frontend** (terminal 2)

```
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, allow the camera, and look straight ahead for a few seconds while it calibrates.

Click **Turn alarm on** once after the page loads. Browsers block sound until you interact with the page.

## Configuration

All thresholds are in `backend/config.py`. The server reloads when you save the file.

| Setting | Default | Meaning |
|---|---|---|
| `EAR_THRESHOLD` | 0.20 | Eye openness below this counts as closed |
| `CLOSED_SECONDS` | 1.5 | Eyes closed this long raises "Eyes closed" |
| `YAW_LIMIT` | 25 | Degrees of left/right head turn from your normal position |
| `PITCH_LIMIT` | 20 | Up/down head tilt from your normal position (approximate units) |
| `AWAY_SECONDS` | 2.0 | Looking away this long raises "Looking away" |
| `CALIBRATION_SECONDS` | 2.0 | Time spent learning your normal head position |
| `CALIBRATION_MIN_FRAMES` | 5 | Minimum frames needed to finish calibration |

Watch the live yaw, pitch and EAR numbers on the page while you move, then adjust the limits to suit your camera and lighting.

## Deployment

The backend runs on Render (Docker) and the frontend on Vercel. The frontend finds the backend through an environment variable.

Full step-by-step settings are in [DEPLOY.md](DEPLOY.md).

## Known limitations

- **Free hosting is slow.** The backend does image processing on a small free server, so results arrive later than on a laptop, and calibration takes a few seconds longer. Run it locally for the best response.
- **Free Render sleeps** after about 15 minutes without traffic. The first visit after that waits up to a minute for it to wake up.
- **Lighting and camera angle matter.** Strong backlight, sunglasses, or a camera far off to the side reduce accuracy. Use Recalibrate if you move.
- **Eyes with glasses** can lower the eye aspect ratio slightly. Adjust `EAR_THRESHOLD` if needed.
- Pitch is an approximate measure, not exact degrees.

## Privacy

Camera frames are sent to the server only to be analysed. They are processed in memory and are **not recorded or stored**. No account or personal data is collected.

## Roadmap

- Phone-use detection with YOLO
- Yawning detection
- Optional saving of session history
- Running face detection in the browser, so the server load stays small