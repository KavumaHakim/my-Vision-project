from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import cv2
import numpy as np

from ultralytics import YOLO

from utils import now_utc

logger = logging.getLogger("vision-v1.detector")


class Detector:
    def __init__(
        self,
        model_path: str,
        use_gpu: bool,
        motion_pixel_threshold: int = 25,
        motion_min_pixels: int = 5000,
        face_after_motion_seconds: float = 10.0,
        fallback_models: list[str] | None = None,
    ) -> None:
        model_candidates = self._model_candidates(model_path, fallback_models or [])
        if not model_candidates:
            raise RuntimeError("No valid model candidates were provided")

        self.model = None
        self.model_source = None
        last_error: Exception | None = None
        for candidate in model_candidates:
            try:
                self.model = YOLO(candidate)
                self.model_source = candidate
                logger.info("Loaded detection model: %s", candidate)
                break
            except Exception as exc:
                last_error = exc
                logger.warning("Failed model candidate '%s': %s", candidate, exc)

        if self.model is None:
            joined = ", ".join(model_candidates)
            raise RuntimeError(f"Failed to load any detection model candidate: {joined}") from last_error

        self.device = "cuda" if use_gpu else "cpu"
        self.model.to(self.device)
        self.motion_pixel_threshold = max(1, int(motion_pixel_threshold))
        self.motion_min_pixels = max(100, int(motion_min_pixels))
        self.face_after_motion_seconds = max(1.0, float(face_after_motion_seconds))

        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._latest_raw: np.ndarray | None = None
        self._latest_detections: list[dict[str, Any]] = []
        self._latest_ts: str | None = None
        self._latest_motion = False
        self._latest_person = False
        self._face_after_motion_until = 0.0
        self._motion_latched = False
        self._post_face_until = 0.0
        self._prev_motion_gray: np.ndarray | None = None

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ready = False

    @staticmethod
    def _is_remote(source: str) -> bool:
        return source.startswith(("http://", "https://"))

    @staticmethod
    def _has_local_hint(source: str) -> bool:
        if source.startswith("."):
            return True
        if os.path.sep in source:
            return True
        if os.path.altsep and os.path.altsep in source:
            return True
        return False

    @classmethod
    def _model_candidates(cls, model_path: str, fallbacks: list[str]) -> list[str]:
        candidates: list[str] = []
        path = (model_path or "").strip()
        if path:
            if cls._is_remote(path) or os.path.exists(path) or not cls._has_local_hint(path):
                candidates.append(path)
            else:
                logger.warning("MODEL_PATH '%s' not found. Falling back to auto-download candidates.", path)
        for item in fallbacks:
            name = (item or "").strip()
            if name and name not in candidates:
                candidates.append(name)
        return candidates

    def start(self, frame_source) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, args=(frame_source,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def is_ready(self) -> bool:
        return self._ready

    def get_model_source(self) -> str | None:
        return self.model_source

    def get_latest(self) -> tuple[str | None, list[dict[str, Any]]]:
        with self._lock:
            return self._latest_ts, list(self._latest_detections)

    def has_label(self, label: str) -> bool:
        with self._lock:
            return any(det.get("label") == label for det in self._latest_detections)

    def has_motion(self) -> bool:
        with self._lock:
            return self._latest_motion

    def has_person(self) -> bool:
        with self._lock:
            return self._latest_person

    def open_post_face_window(self, window_s: float = 8.0) -> None:
        until = time.time() + max(1.0, float(window_s))
        with self._lock:
            self._post_face_until = max(self._post_face_until, until)

    def can_run_post_face_pipeline(self) -> bool:
        with self._lock:
            return time.time() < self._post_face_until

    def can_run_face_pipeline(self) -> bool:
        with self._lock:
            return self._latest_motion or time.time() < self._face_after_motion_until

    def get_latest_frame(self, annotated: bool = True):
        with self._lock:
            frame = self._latest_frame if annotated else self._latest_raw
            if frame is None:
                return None
            return frame.copy()

    def _is_motion_detected(self, frame: np.ndarray) -> bool:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if self._prev_motion_gray is None:
            self._prev_motion_gray = gray
            return False
        delta = cv2.absdiff(self._prev_motion_gray, gray)
        self._prev_motion_gray = gray
        thresh = cv2.threshold(
            delta,
            self.motion_pixel_threshold,
            255,
            cv2.THRESH_BINARY,
        )[1]
        changed = int(cv2.countNonZero(thresh))
        return changed >= self.motion_min_pixels

    def _parse_detections(self, result) -> tuple[list[dict[str, Any]], bool]:
        detections: list[dict[str, Any]] = []
        person_present = False
        if result is None:
            return detections, person_present
        for box in result.boxes:
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            x1, y1, x2, y2 = xyxy
            w = max(0, x2 - x1)
            h = max(0, y2 - y1)
            conf = float(box.conf[0].cpu().item())
            cls_id = int(box.cls[0].cpu().item())
            label = self.model.names.get(cls_id, str(cls_id))
            if label == "person":
                person_present = True
            detections.append(
                {
                    "label": label,
                    "confidence": round(conf, 4),
                    "bbox": [int(x1), int(y1), int(w), int(h)],
                }
            )
        return detections, person_present

    def _draw_detections(self, frame: np.ndarray, detections: list[dict[str, Any]], color=(0, 255, 0)) -> None:
        for det in detections:
            x, y, w, h = det["bbox"]
            x2 = x + w
            y2 = y + h
            label = det["label"]
            conf = float(det["confidence"])
            cv2.rectangle(frame, (x, y), (x2, y2), color, 2)
            text = f"{label} {conf:.2f}"
            cv2.putText(
                frame,
                text,
                (x, max(0, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA,
            )

    def _loop(self, frame_source) -> None:
        while not self._stop.is_set():
            frame = frame_source()
            if frame is None:
                time.sleep(0.02)
                continue

            raw = frame.copy()
            motion_detected = self._is_motion_detected(raw)
            now_ts = time.time()
            if motion_detected and not self._motion_latched:
                self._face_after_motion_until = now_ts + self.face_after_motion_seconds
                self._motion_latched = True
            elif not motion_detected:
                self._motion_latched = False

            detections: list[dict[str, Any]] = []
            person_present = False

            if motion_detected or now_ts < self._face_after_motion_until:
                run_full_detection = self.can_run_post_face_pipeline()
                results = self.model.predict(
                    source=frame,
                    verbose=False,
                    device=self.device,
                    imgsz=640,
                    conf=0.25,
                    classes=None if run_full_detection else [0],
                )
                result = results[0] if results else None
                detections, person_present = self._parse_detections(result)
                self._draw_detections(
                    frame,
                    detections,
                    color=(0, 255, 0) if run_full_detection else (0, 180, 255),
                )

            ts = now_utc().isoformat()
            with self._lock:
                self._latest_frame = frame
                self._latest_raw = raw
                self._latest_detections = detections
                self._latest_ts = ts
                self._latest_motion = motion_detected
                self._latest_person = person_present
                self._ready = True
