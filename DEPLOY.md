# Deploying

Backend on Render, frontend on Vercel. Deploy the backend first, because the frontend needs its URL.

## 0. Before pushing to GitHub
- Make sure `backend/models/face_landmarker.task` exists (it is downloaded the first time you run the backend locally) and is committed, so Render does not download it on every restart.
- Push the whole `driver-monitor` folder to one GitHub repo.

## 1. Backend on Render (Web Service)
| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Environment variable | `PYTHON_VERSION` = `3.12.7` (or another version you tested) |

When it is live, open `https://YOUR-APP.onrender.com/` in a browser. You should see `{"status":"ok"}`.

If the logs show `libGL.so.1` errors, change the Build Command to:
```
pip install -r requirements.txt && pip uninstall -y opencv-python opencv-contrib-python && pip install --force-reinstall --no-deps opencv-contrib-python-headless
```

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
- Open the Vercel link and allow the camera. The status panel should say "Connected".
- Free Render sleeps after about 15 minutes. Open the backend URL once before a demo to wake it up.