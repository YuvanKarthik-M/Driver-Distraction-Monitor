# Driver Monitor

## Run the backend (terminal 1)
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

## Run the frontend (terminal 2)
cd frontend
npm install
npm run dev

Open http://localhost:5173 and allow the camera.
