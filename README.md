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

## Raspberry Pi Deployment

The Pi runs the backend (which also serves the built frontend) behind a
Cloudflare tunnel for a stable public URL.

### Services

```bash
bash scripts/install-services.sh   # installs vision-backend + vision-tunnel systemd units
bash scripts/update.sh             # on the Pi: git pull + restart backend (tunnel URL unchanged)
```

`install-services.sh` auto-detects the tunnel mode: if `~/.cloudflared/config.yml`
exists it runs the named tunnel (stable custom-domain URL); otherwise it falls
back to a quick tunnel (random `trycloudflare.com` URL).

### Named tunnel (stable custom domain)

One-time setup on the Pi (domain's DNS must already be on Cloudflare):

```bash
cloudflared tunnel login
cloudflared tunnel create vision-v1
cloudflared tunnel route dns vision-v1 vision.yourdomain.com   # creates the DNS record
```

Then write `~/.cloudflared/config.yml` — **use `127.0.0.1`, not `localhost`**
(uvicorn binds IPv4 only; `localhost` can resolve to IPv6 `::1` and fail with
"connection refused" / Cloudflare error 1033):

```yaml
tunnel: vision-v1
credentials-file: /home/<user>/.cloudflared/<UUID>.json
ingress:
  - hostname: vision.yourdomain.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

Re-run `bash scripts/install-services.sh` to switch the service onto the named
tunnel. Verify with `journalctl -u vision-tunnel -f` (look for
`Registered tunnel connection`).

### Frontend builds

The Pi serves the committed `frontend/dist`. On your dev machine, push with
`bash scripts/release.sh` (builds the frontend, commits `dist` if it changed,
then pushes) so the Pi always pulls an up-to-date UI.

## Notes

- The system captures an image automatically every `IMAGE_CAPTURE_INTERVAL` seconds.
- Manual capture obeys `UPLOAD_COOLDOWN_SECONDS`.
- Captures are stored in Supabase under `captures/YYYY/MM/DD/`.
- Resource-saving pipeline order: motion -> person stage -> face stage -> full object/action/pose stage.
- Face recognition runs when a person is detected, for `FACE_AFTER_MOTION_SECONDS` after motion first appears.
- Action and pose can both run on YOLO pose models (for example `yolo26pose`) via `ACTION_MODEL_PATH` and `POSE_MODEL_PATH`.
- If `ACTION_MODEL_PATH` is missing locally, backend downloads it from `ACTION_MODEL_URL` (default: `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-pose.pt`) and stores it at the configured action model path.
- If `POSE_MODEL_PATH` is missing locally, backend downloads it from `POSE_MODEL_URL` (default: `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-pose.pt`) and stores it at the configured pose model path.
- Set lightweight fallback order with `AUTO_MODEL_CANDIDATES` (default: `yolo11n.pt,yolov8n.pt`).
- `yolo26n-pose.pt` requires `ultralytics>=8.4.0`.
