from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import cv2
import numpy as np
import requests

from camera import Camera
from config import load_settings
from detector import Detector
from face_db import FaceDB
from face_service import FaceService
from scheduler import CaptureService, FaceRecognitionService
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
    face_recognition_service.start()
    try:
        yield
    finally:
        face_recognition_service.stop()
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

face_db = FaceDB(settings.face_db_path)
face_service = FaceService(model_name=settings.face_model_name, use_gpu=settings.use_gpu)

capture_service = CaptureService(
    detector=detector,
    uploader=uploader,
    interval_s=settings.image_capture_interval,
    cooldown_s=settings.upload_cooldown_seconds,
    capture_dir=settings.capture_dir,
)

face_recognition_service = FaceRecognitionService(
    detector=detector,
    face_service=face_service,
    face_db=face_db,
    threshold=settings.face_match_threshold,
    interval_s=settings.face_recognition_interval,
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


def _best_matches(embedding: np.ndarray, threshold: float, top_k: int = 3) -> list[dict]:
    emb = np.asarray(embedding, dtype=np.float32)
    emb_norm = np.linalg.norm(emb) + 1e-10
    matches: list[dict] = []
    for face_id, name, stored in face_db.iter_embeddings():
        stored_norm = np.linalg.norm(stored) + 1e-10
        score = float(np.dot(emb, stored) / (emb_norm * stored_norm))
        if score >= threshold:
            matches.append({"id": face_id, "name": name, "score": score})
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:top_k]


async def _load_image(source: str, file: UploadFile | None) -> np.ndarray:
    if source == "live":
        frame = camera.read()
        if frame is None:
            raise HTTPException(status_code=503, detail="camera_unavailable")
        return frame
    if file is None:
        raise HTTPException(status_code=400, detail="image_required")
    data = await file.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="invalid_image")
    return img


def _encode_jpeg(frame: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise HTTPException(status_code=500, detail="encode_failed")
    return encoded.tobytes()


@app.get("/faces")
async def list_faces():
    return JSONResponse({"ok": True, "faces": face_db.list_names()})


@app.post("/face/register")
async def face_register(
    name: str = Form(...),
    source: str = Form("upload"),
    file: UploadFile | None = File(None),
):
    if source not in {"upload", "live"}:
        raise HTTPException(status_code=400, detail="invalid_source")
    img = await _load_image(source, file)
    embedding, meta = face_service.get_embedding(img)
    if embedding is None:
        raise HTTPException(status_code=422, detail=meta.get("error", "no_face"))
    face_id = face_db.add(name.strip(), embedding)
    return JSONResponse({"ok": True, "id": face_id, "name": name.strip(), "meta": meta})


@app.post("/face/recognize")
async def face_recognize(
    source: str = Form("upload"),
    file: UploadFile | None = File(None),
):
    if source not in {"upload", "live"}:
        raise HTTPException(status_code=400, detail="invalid_source")
    img = await _load_image(source, file)
    embedding, meta = face_service.get_embedding(img)
    if embedding is None:
        raise HTTPException(status_code=422, detail=meta.get("error", "no_face"))
    matches = _best_matches(embedding, settings.face_match_threshold)
    return JSONResponse(
        {
            "ok": True,
            "threshold": settings.face_match_threshold,
            "best": matches[0] if matches else None,
            "matches": matches,
            "meta": meta,
        }
    )


@app.get("/face/last")
async def face_last():
    return JSONResponse({"ok": True, "result": face_recognition_service.get_last()})


@app.post("/emotion")
async def emotion_detect(
    source: str = Form("upload"),
    file: UploadFile | None = File(None),
):
    if not settings.hf_token:
        raise HTTPException(status_code=500, detail="hf_token_missing")
    if source not in {"upload", "live"}:
        raise HTTPException(status_code=400, detail="invalid_source")

    if source == "live":
        frame = camera.read()
        if frame is None:
            raise HTTPException(status_code=503, detail="camera_unavailable")
        data = _encode_jpeg(frame)
    else:
        if file is None:
            raise HTTPException(status_code=400, detail="image_required")
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="invalid_image")

    headers = {
        "Authorization": f"Bearer {settings.hf_token}",
        "Content-Type": "image/jpeg",
    }
    try:
        resp = requests.post(
            settings.hf_emotion_url,
            headers=headers,
            data=data,
            timeout=30,
        )
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="hf_request_failed")

    try:
        payload = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="hf_invalid_response")

    if resp.status_code >= 400:
        return JSONResponse({"ok": False, "error": payload}, status_code=resp.status_code)
    return JSONResponse({"ok": True, "result": payload})
