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
    face_recognition_interval: int
    face_unknown_threshold: float
    hf_token: str | None
    hf_emotion_url: str
    action_interval: int
    action_window_s: float
    action_frames: int
    audio_interval: int
    audio_window_s: float
    audio_sample_rate: int
    audio_threshold: float
    audio_labels: list[str]
    audio_device: str | None
    hf_audio_url: str | None
    audio_local_model: str | None


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
    face_recognition_interval = int(os.getenv("FACE_RECOGNITION_INTERVAL", "10").strip())
    face_unknown_threshold = float(os.getenv("FACE_UNKNOWN_THRESHOLD", "0.5").strip())
    hf_token = os.getenv("HF_TOKEN", "").strip() or None
    hf_emotion_url = os.getenv(
        "HF_EMOTION_URL",
        "https://router.huggingface.co/hf-inference/models/dima806/facial_emotions_image_detection",
    ).strip()
    action_interval = int(os.getenv("ACTION_INTERVAL", "10").strip())
    action_window_s = float(os.getenv("ACTION_WINDOW_S", "2.0").strip())
    action_frames = int(os.getenv("ACTION_FRAMES", "16").strip())
    audio_interval = int(os.getenv("AUDIO_INTERVAL", "5").strip())
    audio_window_s = float(os.getenv("AUDIO_WINDOW_S", "2.0").strip())
    audio_sample_rate = int(os.getenv("AUDIO_SAMPLE_RATE", "16000").strip())
    audio_threshold = float(os.getenv("AUDIO_THRESHOLD", "0.35").strip())
    audio_labels = [
        label.strip()
        for label in os.getenv("AUDIO_LABELS", "scream,shout,yell,screaming").split(",")
        if label.strip()
    ]
    audio_device = os.getenv("AUDIO_DEVICE", "").strip() or None
    hf_audio_url = os.getenv(
        "HF_AUDIO_URL",
        "https://api-inference.huggingface.co/models/MIT/ast-finetuned-audioset-10-10-0.4593",
    ).strip()
    audio_local_model = os.getenv("AUDIO_LOCAL_MODEL", "").strip() or None

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
        face_recognition_interval=face_recognition_interval,
        face_unknown_threshold=face_unknown_threshold,
        hf_token=hf_token,
        hf_emotion_url=hf_emotion_url,
        action_interval=action_interval,
        action_window_s=action_window_s,
        action_frames=action_frames,
        audio_interval=audio_interval,
        audio_window_s=audio_window_s,
        audio_sample_rate=audio_sample_rate,
        audio_threshold=audio_threshold,
        audio_labels=audio_labels,
        audio_device=audio_device,
        hf_audio_url=hf_audio_url,
        audio_local_model=audio_local_model,
    )
