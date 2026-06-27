from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import cv2
import numpy as np

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
        enable_model: bool = True,
    ) -> None:
        self.model = None
        self._hog = None
        self.model_source = None
        self.model_error: str | None = None
        model_candidates = self._model_candidates(model_path, fallback_models or [])
        if enable_model:
            if not model_candidates:
                self.model_error = "No valid model candidates were provided"
                logger.warning("Detector model unavailable: %s", self.model_error)
            else:
                try:
                    from ultralytics import YOLO
                except Exception as exc:
                    self.model_error = f"ultralytics_import_failed: {exc}"
                    logger.warning("Ultralytics unavailable, attempting OpenCV HOG fallback: %s", self.model_error)
                else:
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
                        self.model_error = f"failed_to_load_candidates: {joined}"
                        logger.warning("Detector model unavailable: %s", self.model_error)
                        if last_error:
                            logger.debug("Last model load error: %s", last_error)

            if self.model is None:
                try:
                    hog = cv2.HOGDescriptor()
                    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
                    self._hog = hog
                    self.model_source = "opencv_hog_default_people_detector"
                    logger.info("Using OpenCV HOG fallback detector (person-only).")
                except Exception as exc:
                    if self.model_error:
                        self.model_error = f"{self.model_error}; hog_init_failed: {exc}"
                    else:
                        self.model_error = f"hog_init_failed: {exc}"
                    logger.warning("Detector fallback disabled: %s", self.model_error)
        else:
            self.model_error = "disabled_by_config"

        self.device = "cuda" if use_gpu else "cpu"
        if self.model is not None:
            # Only PyTorch (.pt) models support .to(); exported formats
            # (ONNX/NCNN/TensorRT) are CPU-resident and ultralytics raises
            # TypeError if you try to move them.
            if str(self.model_source or "").endswith(".pt"):
                self.model.to(self.device)
        self.motion_pixel_threshold = max(1, int(motion_pixel_threshold))
        self.motion_min_pixels = max(100, int(motion_min_pixels))
        self.face_after_motion_seconds = max(1.0, float(face_after_motion_seconds))

        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._latest_raw: np.ndarray | None = None
        self._latest_detections: list[dict[str, Any]] = []
        self._latest_poses: list[dict[str, Any]] = []
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
        return self._ready and (self.model is not None or self._hog is not None)

    def get_model_source(self) -> str | None:
        return self.model_source

    def get_model_error(self) -> str | None:
        return self.model_error

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

    def get_latest_poses(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._latest_poses)

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

    def _parse_poses(self, result) -> list[dict[str, Any]]:
        """Extract person bboxes + COCO keypoints from a YOLO pose result."""
        poses: list[dict[str, Any]] = []
        if result is None:
            return poses
        keypoints_block = getattr(result, "keypoints", None)
        boxes = result.boxes if result.boxes is not None else []
        for idx, box in enumerate(boxes):
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            x1, y1, x2, y2 = xyxy
            conf = float(box.conf[0].cpu().item())
            pose_item: dict[str, Any] = {
                "confidence": round(conf, 4),
                "bbox": [int(x1), int(y1), int(max(0, x2 - x1)), int(max(0, y2 - y1))],
                "keypoints": [],
            }
            if keypoints_block is not None and len(keypoints_block.xy) > idx:
                xy = keypoints_block.xy[idx].cpu().numpy()
                kp_conf = None
                if keypoints_block.conf is not None and len(keypoints_block.conf) > idx:
                    kp_conf = keypoints_block.conf[idx].cpu().numpy()
                for j in range(xy.shape[0]):
                    pose_item["keypoints"].append({
                        "x": float(xy[j][0]),
                        "y": float(xy[j][1]),
                        "confidence": float(kp_conf[j]) if kp_conf is not None else None,
                    })
            poses.append(pose_item)
        return poses

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

    def _hog_detections(self, frame: np.ndarray) -> tuple[list[dict[str, Any]], bool]:
        if self._hog is None:
            return [], False
        rects, weights = self._hog.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
        detections: list[dict[str, Any]] = []
        for i, (x, y, w, h) in enumerate(rects):
            conf = 0.5
            if len(weights) > i:
                conf = float(weights[i])
            detections.append(
                {
                    "label": "person",
                    "confidence": round(max(0.0, min(conf, 1.0)), 4),
                    "bbox": [int(x), int(y), int(w), int(h)],
                }
            )
        return detections, len(detections) > 0

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
                with self._lock:
                    self._face_after_motion_until = now_ts + self.face_after_motion_seconds
                self._motion_latched = True
            elif not motion_detected:
                self._motion_latched = False

            detections: list[dict[str, Any]] = []
            person_present = False

            poses: list[dict[str, Any]] = []
            if motion_detected or now_ts < self._face_after_motion_until:
                if self.model is not None:
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
                    poses = self._parse_poses(result)
                    self._draw_detections(
                        frame,
                        detections,
                        color=(0, 255, 0) if run_full_detection else (0, 180, 255),
                    )
                elif self._hog is not None:
                    detections, person_present = self._hog_detections(frame)
                    self._draw_detections(frame, detections, color=(0, 180, 255))

            ts = now_utc().isoformat()
            with self._lock:
                self._latest_frame = frame
                self._latest_raw = raw
                self._latest_detections = detections
                self._latest_poses = poses
                self._latest_ts = ts
                self._latest_motion = motion_detected
                self._latest_person = person_present
                self._ready = True
