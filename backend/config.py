from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    enable_detector: bool
    enable_face: bool
    enable_action: bool
    enable_pose: bool
    enable_audio: bool
    model_path: str
    model_type: str
    auto_model_candidates: list[str]
    supabase_url: str | None
    supabase_key: str | None
    image_capture_interval: int
    upload_cooldown_seconds: int
    use_gpu: bool
    capture_dir: str
    camera_index: int
    camera_backend: str | None
    camera_open_timeout_s: float
    camera_required: bool
    stream_fps: int
    face_db_path: str
    face_model_name: str
    face_match_threshold: float
    face_recognition_interval: int
    face_unknown_threshold: float
    hf_token: str | None
    action_interval: int
    action_conf_threshold: float
    audio_interval: int
    audio_window_s: float
    audio_sample_rate: int
    audio_threshold: float
    audio_labels: list[str]
    audio_device: str | None
    hf_audio_url: str | None
    audio_local_model: str | None
    security_unknown_seconds: int
    motion_pixel_threshold: int
    motion_min_pixels: int
    face_after_motion_seconds: float
    post_face_window_s: float
    pose_model_path: str | None
    pose_model_url: str | None
    pose_interval: int
    pose_conf_threshold: float


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_settings() -> Settings:
    machine = platform.machine().lower()
    is_arm = machine.startswith("arm") or machine.startswith("aarch64")
    # Pose model is lightweight enough to enable everything on Pi 4 by default.
    enable_detector = _get_bool("ENABLE_DETECTOR", True)
    enable_face = _get_bool("ENABLE_FACE", True)
    enable_action = _get_bool("ENABLE_ACTION", True)
    enable_pose = _get_bool("ENABLE_POSE", True)
    enable_audio = _get_bool("ENABLE_AUDIO", not is_arm)
    model_path = os.getenv("MODEL_PATH", "yolo11n-pose.pt").strip()
    model_type = os.getenv("MODEL_TYPE", "yolo_pose").strip()
    auto_model_candidates = [
        item.strip()
        for item in os.getenv(
            "AUTO_MODEL_CANDIDATES", "yolo11n-pose.pt,yolov8n-pose.pt"
        ).split(",")
        if item.strip()
    ]
    supabase_url = os.getenv("SUPABASE_URL", "").strip() or None
    supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip() or None
    image_capture_interval = int(os.getenv("IMAGE_CAPTURE_INTERVAL", "30").strip())
    upload_cooldown_seconds = int(os.getenv("UPLOAD_COOLDOWN_SECONDS", "10").strip())
    use_gpu = _get_bool("USE_GPU", False)
    capture_dir = os.getenv("CAPTURE_DIR", "captures").strip()
    camera_index = int(os.getenv("CAMERA_INDEX", "0").strip())
    camera_backend = os.getenv("CAMERA_BACKEND", "").strip() or None
    camera_open_timeout_s = float(os.getenv("CAMERA_OPEN_TIMEOUT_S", "5.0").strip())
    camera_required = _get_bool("CAMERA_REQUIRED", False)
    stream_fps = int(os.getenv("STREAM_FPS", "10").strip())
    face_db_path = os.getenv("FACE_DB_PATH", "faces.db").strip()
    face_model_name = os.getenv("FACE_MODEL_NAME", "buffalo_s").strip()
    face_match_threshold = float(os.getenv("FACE_MATCH_THRESHOLD", "0.45").strip())
    face_recognition_interval = int(os.getenv("FACE_RECOGNITION_INTERVAL", "10").strip())
    face_unknown_threshold = float(os.getenv("FACE_UNKNOWN_THRESHOLD", "0.5").strip())
    hf_token = os.getenv("HF_TOKEN", "").strip() or None
    action_interval = int(os.getenv("ACTION_INTERVAL", "10").strip())
    action_conf_threshold = float(os.getenv("ACTION_CONF_THRESHOLD", "0.5").strip())
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
    security_unknown_seconds = int(os.getenv("SECURITY_UNKNOWN_SECONDS", "5").strip())
    motion_pixel_threshold = int(os.getenv("MOTION_PIXEL_THRESHOLD", "25").strip())
    motion_min_pixels = int(os.getenv("MOTION_MIN_PIXELS", "5000").strip())
    face_after_motion_seconds = float(os.getenv("FACE_AFTER_MOTION_SECONDS", "10.0").strip())
    post_face_window_s = float(os.getenv("POST_FACE_WINDOW_S", "8.0").strip())
    pose_model_path = os.getenv("POSE_MODEL_PATH", "").strip() or None
    pose_model_url = os.getenv(
        "POSE_MODEL_URL",
        os.getenv(
            "ACTION_MODEL_URL",
            "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n-pose.pt",
        ),
    ).strip() or None
    pose_interval = int(os.getenv("POSE_INTERVAL", "10").strip())
    pose_conf_threshold = float(os.getenv("POSE_CONF_THRESHOLD", "0.25").strip())

    return Settings(
        enable_detector=enable_detector,
        enable_face=enable_face,
        enable_action=enable_action,
        enable_pose=enable_pose,
        enable_audio=enable_audio,
        model_path=model_path,
        model_type=model_type,
        auto_model_candidates=auto_model_candidates,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        image_capture_interval=image_capture_interval,
        upload_cooldown_seconds=upload_cooldown_seconds,
        use_gpu=use_gpu,
        capture_dir=capture_dir,
        camera_index=camera_index,
        camera_backend=camera_backend,
        camera_open_timeout_s=camera_open_timeout_s,
        camera_required=camera_required,
        stream_fps=stream_fps,
        face_db_path=face_db_path,
        face_model_name=face_model_name,
        face_match_threshold=face_match_threshold,
        face_recognition_interval=face_recognition_interval,
        face_unknown_threshold=face_unknown_threshold,
        hf_token=hf_token,
        action_interval=action_interval,
        action_conf_threshold=action_conf_threshold,
        audio_interval=audio_interval,
        audio_window_s=audio_window_s,
        audio_sample_rate=audio_sample_rate,
        audio_threshold=audio_threshold,
        audio_labels=audio_labels,
        audio_device=audio_device,
        hf_audio_url=hf_audio_url,
        audio_local_model=audio_local_model,
        security_unknown_seconds=security_unknown_seconds,
        motion_pixel_threshold=motion_pixel_threshold,
        motion_min_pixels=motion_min_pixels,
        face_after_motion_seconds=face_after_motion_seconds,
        post_face_window_s=post_face_window_s,
        pose_model_path=pose_model_path,
        pose_model_url=pose_model_url,
        pose_interval=pose_interval,
        pose_conf_threshold=pose_conf_threshold,
    )
