from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    model_path: str
    model_type: str
    supabase_url: str | None
    supabase_key: str | None
    image_capture_interval: int
    upload_cooldown_seconds: int
    use_gpu: bool
    capture_dir: str
    camera_index: int
    stream_fps: int
    face_db_path: str
    face_model_name: str
    face_match_threshold: float


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    model_path = os.getenv("MODEL_PATH", "").strip()
    model_type = os.getenv("MODEL_TYPE", "yolov8").strip()
    supabase_url = os.getenv("SUPABASE_URL", "").strip() or None
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip() or None
    image_capture_interval = int(os.getenv("IMAGE_CAPTURE_INTERVAL", "30").strip())
    upload_cooldown_seconds = int(os.getenv("UPLOAD_COOLDOWN_SECONDS", "10").strip())
    use_gpu = _get_bool("USE_GPU", False)
    capture_dir = os.getenv("CAPTURE_DIR", "captures").strip()
    camera_index = int(os.getenv("CAMERA_INDEX", "0").strip())
    stream_fps = int(os.getenv("STREAM_FPS", "10").strip())
    face_db_path = os.getenv("FACE_DB_PATH", "faces.db").strip()
    face_model_name = os.getenv("FACE_MODEL_NAME", "buffalo_l").strip()
    face_match_threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.45").strip())

    return Settings(
        model_path=model_path,
        model_type=model_type,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        image_capture_interval=image_capture_interval,
        upload_cooldown_seconds=upload_cooldown_seconds,
        use_gpu=use_gpu,
        capture_dir=capture_dir,
        camera_index=camera_index,
        stream_fps=stream_fps,
        face_db_path=face_db_path,
        face_model_name=face_model_name,
        face_match_threshold=face_match_threshold,
    )
