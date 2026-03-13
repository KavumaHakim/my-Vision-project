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
   - If `MODEL_PATH` is missing or not found, backend auto-falls back to `AUTO_MODEL_CANDIDATES` and downloads the first available lightweight model.

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
- `GET /face/last-crop` latest cropped face from the recognition pipeline
- `GET /pose/last` latest pose tracking result (when pose model is configured)
- `GET /crowd/last` fused behavior + crowd analysis using object detections and pose actions
- `GET /models/toggles` current frontend-controlled model switches
- `POST /models/toggles` update one or more model switches at runtime
- `GET /camera/source` current camera source (index or URL)
- `POST /camera/source` switch camera source to a device index or network stream URL

## Notes

- The system captures an image automatically every `IMAGE_CAPTURE_INTERVAL` seconds.
- Manual capture obeys `UPLOAD_COOLDOWN_SECONDS`.
- Captures are stored in Supabase under `captures/YYYY/MM/DD/`.
- Resource-saving pipeline order: motion -> person stage -> face stage -> full object/action/pose stage.
- Face recognition runs when a person is detected, for `FACE_AFTER_MOTION_SECONDS` after motion first appears.
- Action and pose can both run on YOLO pose models (for example `yolo26pose`) via `ACTION_MODEL_PATH` and `POSE_MODEL_PATH`.
- If `ACTION_MODEL_PATH` is missing locally, backend downloads it from `ACTION_MODEL_URL` (default: `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-pose.pt`) and stores it at the configured action model path.
- If `POSE_MODEL_PATH` is missing locally, backend downloads it from `POSE_MODEL_URL` (default: `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-pose.pt`) and stores it at the configured pose model path.
- Crowd/behavior analytics cadence and thresholds can be tuned with `CROWD_INTERVAL`, `CROWD_BEHAVIOR_THRESHOLD`, `CROWD_MEDIUM_COUNT`, `CROWD_HIGH_COUNT`, `CROWD_MEDIUM_OCCUPANCY`, and `CROWD_HIGH_OCCUPANCY`.
- Model execution can be toggled live from the dashboard (`object_detection`, `face_recognition`, `emotion`, `action_tracking`, `pose_tracking`, `audio_alerts`, `crowd_analysis`).
- Set lightweight fallback order with `AUTO_MODEL_CANDIDATES` (default: `yolo11n.pt,yolov8n.pt`).
- `yolo26n-pose.pt` requires `ultralytics>=8.4.0`.
- Offline startup is supported: if remote model downloads fail, the app starts in degraded mode and reports disabled services in `/health`.
- The UI prompts for a camera endpoint URL (e.g. Raspberry Pi MJPEG/RTSP stream). Use `0` to revert to local webcam.
