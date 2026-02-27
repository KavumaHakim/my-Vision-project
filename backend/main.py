from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Response
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
from action_service import ActionService
from audio_alert_service import AudioAlertService
from scheduler import CaptureService, FaceRecognitionService, EmotionService, ActionTrackingService
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
    emotion_service.start()
    action_tracking_service.start()
    audio_alert_service.start()
    try:
        yield
    finally:
        audio_alert_service.stop()
        action_tracking_service.stop()
        emotion_service.stop()
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
    unknown_threshold=settings.face_unknown_threshold,
    interval_s=settings.face_recognition_interval,
    security_unknown_seconds=settings.security_unknown_seconds,
)

emotion_service = EmotionService(
    detector=detector,
    hf_url=settings.hf_emotion_url,
    hf_token=settings.hf_token,
    interval_s=settings.face_recognition_interval,
    threshold=settings.emotion_conf_threshold,
)

action_service = ActionService(
    detector=detector,
    interval_s=settings.action_interval,
    window_s=settings.action_window_s,
    frames=settings.action_frames,
    use_gpu=settings.use_gpu,
)

action_tracking_service = ActionTrackingService(
    detector=detector,
    action_service=action_service,
    face_db=face_db,
    interval_s=settings.action_interval,
    threshold=settings.action_conf_threshold,
)

audio_alert_service = AudioAlertService(
    face_db=face_db,
    hf_url=settings.hf_audio_url,
    hf_token=settings.hf_token,
    labels=settings.audio_labels,
    threshold=settings.audio_threshold,
    interval_s=settings.audio_interval,
    window_s=settings.audio_window_s,
    sample_rate=settings.audio_sample_rate,
    device=settings.audio_device,
    local_model=settings.audio_local_model,
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
        mjpeg_generator(detector, fps=settings.stream_fps, face_recognition_service=face_recognition_service),
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

def _best_unknown(embedding: np.ndarray, threshold: float) -> tuple[int | None, float]:
    emb = np.asarray(embedding, dtype=np.float32)
    emb_norm = np.linalg.norm(emb) + 1e-10
    best_id = None
    best_score = 0.0
    for unknown_id, stored in face_db.iter_unknown_embeddings():
        stored_norm = np.linalg.norm(stored) + 1e-10
        score = float(np.dot(emb, stored) / (emb_norm * stored_norm))
        if score > best_score:
            best_score = score
            best_id = unknown_id
    if best_id is None or best_score < threshold:
        return None, best_score
    return best_id, best_score


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
    faces = face_service.get_faces(img)
    if not faces:
        raise HTTPException(status_code=422, detail="no_face")
    results = []
    best_overall = None
    best_score = 0.0
    for face in faces:
        embedding = face["embedding"]
        bbox = face["bbox"]
        matches = _best_matches(embedding, settings.face_match_threshold)
        if matches:
            best = matches[0]
            if best["score"] > best_score:
                best_overall = best
                best_score = best["score"]
            results.append({"bbox": bbox, "best": best, "matches": matches})
            continue

        unknown_id, unknown_score = _best_unknown(embedding, settings.face_unknown_threshold)
        if unknown_id is None:
            unknown_id = face_db.add_unknown(embedding)
        else:
            face_db.update_unknown(unknown_id, embedding)
        unknown_name = f"Unknown #{unknown_id}"
        results.append(
            {
                "bbox": bbox,
                "best": {"id": unknown_id, "name": unknown_name, "score": unknown_score},
                "matches": [],
            }
        )
    matches = best_overall
    return JSONResponse(
        {
            "ok": True,
            "threshold": settings.face_match_threshold,
            "best": matches,
            "faces": results,
        }
    )


@app.get("/face/last")
async def face_last():
    return JSONResponse({"ok": True, "result": face_recognition_service.get_last()})


@app.get("/security/last")
async def security_last():
    return JSONResponse({"ok": True, "result": face_recognition_service.get_security_status()})


@app.get("/security/unknown-frame")
async def security_unknown_frame(unknown_id: int | None = None):
    status = face_recognition_service.get_security_status()
    unknowns = status.get("unknowns") or []
    if not unknowns:
        raise HTTPException(status_code=404, detail="no_unknowns")
    if unknown_id is None:
        target = unknowns[0]
    else:
        target = next((item for item in unknowns if item.get("id") == unknown_id), None)
        if target is None:
            raise HTTPException(status_code=404, detail="unknown_not_found")
    bbox = target.get("bbox")
    if not bbox or len(bbox) != 4:
        raise HTTPException(status_code=404, detail="bbox_missing")

    frame = detector.get_latest_frame(annotated=False)
    if frame is None:
        raise HTTPException(status_code=503, detail="no_frame")
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1 = max(0, min(x1, frame.shape[1] - 1))
    x2 = max(0, min(x2, frame.shape[1]))
    y1 = max(0, min(y1, frame.shape[0] - 1))
    y2 = max(0, min(y2, frame.shape[0]))
    if x2 <= x1 or y2 <= y1:
        raise HTTPException(status_code=400, detail="invalid_bbox")
    crop = frame[y1:y2, x1:x2]
    ok, encoded = cv2.imencode(".jpg", crop)
    if not ok:
        raise HTTPException(status_code=500, detail="encode_failed")
    return Response(content=encoded.tobytes(), media_type="image/jpeg")


@app.get("/timeline")
async def timeline(limit: int = 100):
    limit = max(1, min(int(limit), 500))
    return JSONResponse({"ok": True, "events": face_db.list_events(limit=limit)})


@app.get("/attendance")
async def attendance(limit: int = 50):
    limit = max(1, min(int(limit), 200))
    return JSONResponse({"ok": True, "records": face_db.list_attendance(limit=limit)})


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
        logger.warning("HF emotion error %s: %s", resp.status_code, payload)
        return JSONResponse({"ok": False, "error": payload}, status_code=resp.status_code)
    return JSONResponse({"ok": True, "result": payload})


@app.get("/emotion/last")
async def emotion_last():
    return JSONResponse({"ok": True, "result": emotion_service.get_last()})


@app.get("/action/last")
async def action_last():
    return JSONResponse({"ok": True, "result": action_tracking_service.get_last()})


@app.get("/audio/last")
async def audio_last():
    return JSONResponse({"ok": True, "result": audio_alert_service.get_last()})
