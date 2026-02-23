from __future__ import annotations

import os
import threading
import time
from typing import Any

import cv2

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
            self.request_capture(reason="auto")
