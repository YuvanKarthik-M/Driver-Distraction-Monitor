# Deploying

Backend on Render (Docker), frontend on Vercel. Deploy the backend first, because the frontend needs its URL.

## 0. Before pushing to GitHub
- Make sure `backend/models/face_landmarker.task` exists (it is downloaded the first time you run the backend locally) and is committed.
- Push the whole `driver-monitor` folder to one GitHub repo. `backend/Dockerfile` must be included.

## 1. Backend on Render (Web Service, Docker)
MediaPipe needs system libraries (`libGLESv2`) that Render's plain Python runtime does not have, so the backend runs in Docker.

| Setting | Value |
|---|---|
| Language / Runtime | Docker |
| Root Directory | `backend` |
| Dockerfile Path | `./Dockerfile` (default) |
| Build / Start Command | leave empty (the Dockerfile handles both) |
| Instance Type | Free |

No `PYTHON_VERSION` variable is needed; the Dockerfile uses Python 3.12.

When it is live, open `https://YOUR-APP.onrender.com/` in a browser. You should see `{"status":"ok"}`.

## 2. Frontend on Vercel
| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Environment variable | `VITE_WS_URL` = `wss://YOUR-APP.onrender.com/ws` |

Note: `wss://` (not `ws://`), and the value ends with `/ws`. Vite reads the variable at build time, so after changing it, redeploy the frontend.

## 3. Checks
- Open the Vercel link and allow the camera. The status panel should say "Connected" and then show your status.
- Free Render sleeps after about 15 minutes. Open the backend URL once before a demo to wake it up.