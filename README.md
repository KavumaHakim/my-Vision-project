# Vision V1

Local AI vision system with FastAPI + React. AI runs on the laptop and the browser consumes the stream + APIs.

## Backend Setup

1. Create a Python 3.10+ virtual environment.
2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Create `backend/.env` from the example:

```bash
copy backend\.env.example backend\.env
```

4. Download a YOLOv8 model (example: `yolov8n.pt`) and set `MODEL_PATH` in `backend/.env`.

5. Start the backend:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Supabase Storage

- Create a Supabase project and a storage bucket named `captures`.
- Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `backend/.env`.
- Ensure the bucket allows uploads with the anon key (or use a service role key for local testing).

## Frontend Setup

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Create `frontend/.env` from the example:

```bash
copy .env.example .env
```

3. Start the frontend:

```bash
npm run dev
```

## Launcher (Windows PowerShell)

From the repo root:

```powershell
.\launch.ps1
```

Options:

```powershell
.\launch.ps1 -BackendPort 8000 -FrontendPort 5173
```

## Endpoints

- `GET /video-stream` MJPEG stream with boxes
- `GET /detections` latest detections
- `POST /capture` capture + upload
- `GET /health` status

## Notes

- The system captures an image automatically every `IMAGE_CAPTURE_INTERVAL` seconds.
- Manual capture obeys `UPLOAD_COOLDOWN_SECONDS`.
- Captures are stored in Supabase under `captures/YYYY/MM/DD/`.
