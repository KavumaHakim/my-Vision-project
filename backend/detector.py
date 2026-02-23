from __future__ import annotations

import threading
import time
from typing import Any

import cv2
import numpy as np

from ultralytics import YOLO

from utils import now_utc


class Detector:
    def __init__(self, model_path: str, use_gpu: bool) -> None:
        if not model_path:
            raise RuntimeError("MODEL_PATH is required")
        self.model = YOLO(model_path)
        self.device = "cuda" if use_gpu else "cpu"
        self.model.to(self.device)

        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._latest_raw: np.ndarray | None = None
        self._latest_detections: list[dict[str, Any]] = []
        self._latest_ts: str | None = None

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ready = False

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

    def get_latest(self) -> tuple[str | None, list[dict[str, Any]]]:
        with self._lock:
            return self._latest_ts, list(self._latest_detections)

    def has_label(self, label: str) -> bool:
        with self._lock:
            return any(det.get("label") == label for det in self._latest_detections)

    def get_latest_frame(self, annotated: bool = True):
        with self._lock:
            frame = self._latest_frame if annotated else self._latest_raw
            if frame is None:
                return None
            return frame.copy()

    def _loop(self, frame_source) -> None:
        while not self._stop.is_set():
            frame = frame_source()
            if frame is None:
                time.sleep(0.02)
                continue

            raw = frame.copy()
            results = self.model.predict(
                source=frame,
                verbose=False,
                device=self.device,
                imgsz=640,
                conf=0.25,
            )
            detections: list[dict[str, Any]] = []

            if results:
                result = results[0]
                for box in result.boxes:
                    xyxy = box.xyxy[0].cpu().numpy().tolist()
                    x1, y1, x2, y2 = xyxy
                    w = max(0, x2 - x1)
                    h = max(0, y2 - y1)
                    conf = float(box.conf[0].cpu().item())
                    cls_id = int(box.cls[0].cpu().item())
                    label = self.model.names.get(cls_id, str(cls_id))

                    detections.append(
                        {
                            "label": label,
                            "confidence": round(conf, 4),
                            "bbox": [int(x1), int(y1), int(w), int(h)],
                        }
                    )

                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    text = f"{label} {conf:.2f}"
                    cv2.putText(
                        frame,
                        text,
                        (int(x1), max(0, int(y1) - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                        cv2.LINE_AA,
                    )

            ts = now_utc().isoformat()
            with self._lock:
                self._latest_frame = frame
                self._latest_raw = raw
                self._latest_detections = detections
                self._latest_ts = ts
                self._ready = True
