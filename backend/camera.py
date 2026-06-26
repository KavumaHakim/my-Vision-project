from __future__ import annotations

import logging
import threading
import time

import cv2

logger = logging.getLogger("vision-v1.camera")

_WARMUP_ATTEMPTS = 20
_WARMUP_DELAY   = 0.1   # seconds between warmup read attempts
_FAIL_LOG_EVERY = 100   # log a warning every N consecutive read failures


class Camera:
    def __init__(self, index: int = 0, backend: int | None = None) -> None:
        self.index   = index
        self.backend = backend
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()
        self._consecutive_failures = 0

    def open(self, timeout_s: float = 5.0) -> None:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                return

        result: dict = {"cap": None, "error": None}

        def _open_worker() -> None:
            try:
                cap = (
                    cv2.VideoCapture(self.index, self.backend)
                    if self.backend is not None
                    else cv2.VideoCapture(self.index)
                )
                if not cap.isOpened():
                    cap.release()
                    result["error"] = RuntimeError("VideoCapture.isOpened() returned False")
                    return
                result["cap"] = cap
            except Exception as exc:
                result["error"] = exc

        thread = threading.Thread(target=_open_worker, daemon=True)
        thread.start()
        thread.join(timeout=max(0.1, float(timeout_s)))

        if thread.is_alive():
            raise RuntimeError(f"Timed out opening camera after {timeout_s:.1f}s")
        if result["error"] is not None:
            raise RuntimeError(str(result["error"]))
        cap = result["cap"]
        if cap is None:
            raise RuntimeError("Failed to open camera")

        with self._lock:
            if self._cap is None:
                self._cap = cap
            else:
                cap.release()
                return

        # Warm-up: confirm the camera actually delivers frames.
        # Some Pi camera setups open without error but need a moment
        # before cap.read() returns valid data.
        for attempt in range(_WARMUP_ATTEMPTS):
            ok, _ = cap.read()
            if ok:
                logger.info(
                    "Camera %d ready (backend=%s, warmup after %d attempt(s))",
                    self.index,
                    self.backend,
                    attempt + 1,
                )
                return
            time.sleep(_WARMUP_DELAY)

        logger.warning(
            "Camera %d opened but produced no frames after %d warmup attempts. "
            "Try setting CAMERA_BACKEND=V4L2 in .env for Pi Camera Module.",
            self.index,
            _WARMUP_ATTEMPTS,
        )

    def close(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def is_opened(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened()

    def read(self):
        with self._lock:
            cap = self._cap
        if cap is None or not cap.isOpened():
            return None
        ok, frame = cap.read()
        if not ok:
            self._consecutive_failures += 1
            if self._consecutive_failures % _FAIL_LOG_EVERY == 1:
                logger.warning(
                    "Camera read failed (consecutive failures: %d). "
                    "If this persists try CAMERA_BACKEND=V4L2 in .env.",
                    self._consecutive_failures,
                )
            time.sleep(0.05)
            return None
        self._consecutive_failures = 0
        return frame
