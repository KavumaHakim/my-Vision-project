from __future__ import annotations

import os
import threading
import time
from typing import Any

import cv2
import numpy as np

from uploader import build_storage_path
from utils import dated_path, ensure_dir, now_utc, timestamp_str


class CaptureService:
    def __init__(self, detector, uploader, interval_s: int, cooldown_s: int, capture_dir: str) -> None:
        self.detector = detector
        self.uploader = uploader
        self.interval_s = max(5, interval_s)
        self.cooldown_s = max(1, cooldown_s)
        self.capture_dir = capture_dir

        self._last_capture = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def request_capture(self, reason: str = "manual") -> dict[str, Any]:
        now = time.time()
        with self._lock:
            if now - self._last_capture < self.cooldown_s:
                return {"ok": False, "error": "cooldown", "reason": reason}
            self._last_capture = now

        return self._capture(reason=reason)

    def _capture(self, reason: str) -> dict[str, Any]:
        frame = self.detector.get_latest_frame(annotated=True)
        if frame is None:
            return {"ok": False, "error": "no_frame", "reason": reason}

        ts = now_utc()
        filename = f"{timestamp_str()}.jpg"
        local_folder = dated_path(self.capture_dir, ts)
        ensure_dir(local_folder)
        local_path = os.path.join(local_folder, filename)

        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            return {"ok": False, "error": "encode_failed", "reason": reason}

        with open(local_path, "wb") as f:
            f.write(encoded.tobytes())

        storage_path = build_storage_path(filename)
        upload = self.uploader.upload_image(storage_path, encoded.tobytes())

        if upload.get("ok"):
            try:
                os.remove(local_path)
            except OSError:
                pass

        return {
            "ok": upload.get("ok", False),
            "reason": reason,
            "local_path": local_path,
            "upload_url": upload.get("url"),
            "error": upload.get("error"),
        }

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self.interval_s)
            if self.detector.has_label("person"):
                self.request_capture(reason="auto")


class FaceRecognitionService:
    def __init__(self, detector, face_service, face_db, threshold: float, interval_s: int) -> None:
        self.detector = detector
        self.face_service = face_service
        self.face_db = face_db
        self.threshold = float(threshold)
        self.interval_s = max(5, int(interval_s))

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_result: dict[str, Any] | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def get_last(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._last_result) if self._last_result else None

    def _set_last(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._last_result = payload

    def _best_matches(self, embedding) -> list[dict[str, Any]]:
        emb = np.asarray(embedding, dtype=np.float32)
        emb_norm = np.linalg.norm(emb) + 1e-10
        matches: list[dict[str, Any]] = []
        for face_id, name, stored in self.face_db.iter_embeddings():
            stored_norm = np.linalg.norm(stored) + 1e-10
            score = float(np.dot(emb, stored) / (emb_norm * stored_norm))
            if score >= self.threshold:
                matches.append({"id": face_id, "name": name, "score": score})
        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:3]

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self.interval_s)
            if not self.detector.has_label("person"):
                continue
            frame = self.detector.get_latest_frame(annotated=False)
            if frame is None:
                continue
            embedding, meta = self.face_service.get_embedding(frame)
            if embedding is None:
                self._set_last(
                    {
                        "ok": False,
                        "error": meta.get("error", "no_face"),
                        "timestamp": now_utc().isoformat(),
                    }
                )
                continue
            matches = self._best_matches(embedding)
            self._set_last(
                {
                    "ok": True,
                    "best": matches[0] if matches else None,
                    "matches": matches,
                    "threshold": self.threshold,
                    "timestamp": now_utc().isoformat(),
                    "meta": meta,
                }
            )
