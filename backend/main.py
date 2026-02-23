from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from camera import Camera
from config import load_settings
from detector import Detector
from scheduler import CaptureService
from streamer import mjpeg_generator
from uploader import SupabaseUploader
from utils import ensure_dir, setup_logging


settings = load_settings()
setup_logging()
logger = logging.getLogger("vision-v1")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dir(settings.capture_dir)
    try:
        camera.open()
    except RuntimeError as exc:
        logger.error("Camera failed to open: %s", exc)
        raise
    detector.start(camera.read)
    capture_service.start()
    try:
        yield
    finally:
        capture_service.stop()
        detector.stop()
        camera.close()


app = FastAPI(title="Vision V1", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

camera = Camera(index=settings.camera_index)

detector = Detector(model_path=settings.model_path, use_gpu=settings.use_gpu)

uploader = SupabaseUploader(settings.supabase_url, settings.supabase_key)

capture_service = CaptureService(
    detector=detector,
    uploader=uploader,
    interval_s=settings.image_capture_interval,
    cooldown_s=settings.upload_cooldown_seconds,
    capture_dir=settings.capture_dir,
)


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "camera": camera.is_opened(),
            "model": detector.is_ready(),
            "uploader": uploader.enabled,
        }
    )


@app.get("/video-stream")
async def video_stream():
    if not camera.is_opened():
        raise HTTPException(status_code=503, detail="camera_unavailable")
    return StreamingResponse(
        mjpeg_generator(detector, fps=settings.stream_fps),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/detections")
async def detections():
    ts, objs = detector.get_latest()
    return JSONResponse({"timestamp": ts, "objects": objs})


@app.post("/capture")
async def capture():
    if not camera.is_opened():
        raise HTTPException(status_code=503, detail="camera_unavailable")
    result = capture_service.request_capture(reason="manual")
    if not result.get("ok"):
        return JSONResponse(result, status_code=429 if result.get("error") == "cooldown" else 500)
    return JSONResponse(result)
