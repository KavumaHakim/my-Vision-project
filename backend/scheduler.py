from __future__ import annotations

import os
import threading
import time
from typing import Any

import cv2
import numpy as np
import requests

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
    def __init__(
        self,
        detector,
        face_service,
        face_db,
        threshold: float,
        unknown_threshold: float,
        interval_s: int,
    ) -> None:
        self.detector = detector
        self.face_service = face_service
        self.face_db = face_db
        self.threshold = float(threshold)
        self.unknown_threshold = float(unknown_threshold)
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

    def _best_unknown(self, embedding) -> tuple[int | None, float]:
        emb = np.asarray(embedding, dtype=np.float32)
        emb_norm = np.linalg.norm(emb) + 1e-10
        best_id = None
        best_score = 0.0
        for unknown_id, stored in self.face_db.iter_unknown_embeddings():
            stored_norm = np.linalg.norm(stored) + 1e-10
            score = float(np.dot(emb, stored) / (emb_norm * stored_norm))
            if score > best_score:
                best_score = score
                best_id = unknown_id
        if best_id is None or best_score < self.unknown_threshold:
            return None, best_score
        return best_id, best_score

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self.interval_s)
            if not self.detector.has_label("person"):
                continue
            frame = self.detector.get_latest_frame(annotated=False)
            if frame is None:
                continue
            faces = self.face_service.get_faces(frame)
            if not faces:
                self._set_last(
                    {
                        "ok": False,
                        "error": "no_face",
                        "timestamp": now_utc().isoformat(),
                        "faces": [],
                    }
                )
                continue

            results: list[dict[str, Any]] = []
            best_overall = None
            best_score = 0.0
            for face in faces:
                embedding = face["embedding"]
                bbox = face["bbox"]
                matches = self._best_matches(embedding)
                if matches:
                    best = matches[0]
                    if best["score"] > best_score:
                        best_overall = best
                        best_score = best["score"]
                    self.face_db.add_event(
                        event_type="face_recognized",
                        face_type="known",
                        face_id=best["id"],
                        name=best["name"],
                        score=best["score"],
                        bbox=bbox,
                    )
                    results.append({"bbox": bbox, "best": best, "matches": matches})
                    continue

                unknown_id, unknown_score = self._best_unknown(embedding)
                if unknown_id is None:
                    unknown_id = self.face_db.add_unknown(embedding)
                else:
                    self.face_db.update_unknown(unknown_id, embedding)
                unknown_name = f"Unknown #{unknown_id}"
                self.face_db.add_event(
                    event_type="face_recognized",
                    face_type="unknown",
                    face_id=unknown_id,
                    name=unknown_name,
                    score=unknown_score,
                    bbox=bbox,
                )
                results.append(
                    {
                        "bbox": bbox,
                        "best": {"id": unknown_id, "name": unknown_name, "score": unknown_score},
                        "matches": [],
                    }
                )

            self._set_last(
                {
                    "ok": True,
                    "best": best_overall,
                    "faces": results,
                    "threshold": self.threshold,
                    "timestamp": now_utc().isoformat(),
                }
            )


class EmotionService:
    def __init__(self, detector, hf_url: str, hf_token: str | None, interval_s: int) -> None:
        self.detector = detector
        self.hf_url = hf_url
        self.hf_token = hf_token
        self.interval_s = max(5, int(interval_s))

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_result: dict[str, Any] | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        if not self.hf_token:
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

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self.interval_s)
            if not self.detector.has_label("person"):
                continue
            frame = self.detector.get_latest_frame(annotated=False)
            if frame is None:
                continue
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            headers = {
                "Authorization": f"Bearer {self.hf_token}",
                "Content-Type": "image/jpeg",
            }
            try:
                resp = requests.post(
                    self.hf_url,
                    headers=headers,
                    data=encoded.tobytes(),
                    timeout=30,
                )
                payload = resp.json()
            except Exception:
                self._set_last(
                    {"ok": False, "error": "hf_request_failed", "timestamp": now_utc().isoformat()}
                )
                continue

            if resp.status_code >= 400:
                self._set_last(
                    {
                        "ok": False,
                        "error": payload,
                        "timestamp": now_utc().isoformat(),
                    }
                )
                continue

            self._set_last(
                {"ok": True, "result": payload, "timestamp": now_utc().isoformat()}
            )
