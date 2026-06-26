from __future__ import annotations

import logging
import threading
import time

import cv2

logger = logging.getLogger("vision-v1.camera")

_WARMUP_ATTEMPTS = 20
_WARMUP_DELAY    = 0.1
_FAIL_LOG_EVERY  = 100


class Camera:
    def __init__(self, index: int = 0, backend: int | None = None) -> None:
        self.index   = index
        self.backend = backend
        self._cap: cv2.VideoCapture | None = None
        self._picam2 = None
        self._lock = threading.Lock()
        self._consecutive_failures = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def open(self, timeout_s: float = 5.0) -> None:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                return
            if self._picam2 is not None:
                return

        cap = self._open_opencv(timeout_s)

        with self._lock:
            self._cap = cap

        # Warmup: confirm the camera actually delivers frames.
        for attempt in range(_WARMUP_ATTEMPTS):
            ok, _ = cap.read()
            if ok:
                logger.info(
                    "Camera %d ready via OpenCV (backend=%s, warmup after %d attempt(s))",
                    self.index, self.backend, attempt + 1,
                )
                return
            time.sleep(_WARMUP_DELAY)

        # V4L2 opened but produced no frames — Pi libcamera camera detected.
        # Release and try picamera2.
        logger.warning(
            "Camera %d: OpenCV/V4L2 produced no frames after %d attempts — "
            "switching to picamera2 (IMX219 / Pi Camera Module on Bookworm).",
            self.index, _WARMUP_ATTEMPTS,
        )
        with self._lock:
            self._cap = None
        cap.release()

        if not self._open_picamera2():
            raise RuntimeError(
                f"Camera {self.index}: both OpenCV V4L2 and picamera2 failed. "
                "Check the ribbon cable and run: sudo rpicam-hello --list-cameras"
            )

    def close(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
            if self._picam2 is not None:
                try:
                    self._picam2.stop()
                    self._picam2.close()
                except Exception:
                    pass
                self._picam2 = None

    def is_opened(self) -> bool:
        with self._lock:
            if self._picam2 is not None:
                return True
            return self._cap is not None and self._cap.isOpened()

    def read(self):
        with self._lock:
            picam2 = self._picam2
            cap    = self._cap

        if picam2 is not None:
            return self._read_picamera2(picam2)

        return self._read_opencv(cap)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_opencv(self, timeout_s: float) -> cv2.VideoCapture:
        result: dict = {"cap": None, "error": None}

        def _worker() -> None:
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

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout=max(0.1, float(timeout_s)))

        if t.is_alive():
            raise RuntimeError(f"Timed out opening camera after {timeout_s:.1f}s")
        if result["error"] is not None:
            raise RuntimeError(str(result["error"]))
        if result["cap"] is None:
            raise RuntimeError("Failed to open camera")
        return result["cap"]

    def _open_picamera2(self) -> bool:
        try:
            from picamera2 import Picamera2  # type: ignore
        except ImportError:
            logger.warning(
                "Camera %d: picamera2 not installed. "
                "Run: pip install picamera2",
                self.index,
            )
            return False

        try:
            picam2 = Picamera2(self.index)
            config = picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (640, 480)}
            )
            picam2.configure(config)
            picam2.start()
            time.sleep(0.5)
            frame = picam2.capture_array()
            if frame is None or frame.size == 0:
                picam2.stop()
                picam2.close()
                logger.warning("Camera %d: picamera2 started but returned an empty frame.", self.index)
                return False
            with self._lock:
                self._picam2 = picam2
            logger.info("Camera %d ready via picamera2 (IMX219).", self.index)
            return True
        except Exception as exc:
            logger.warning("Camera %d: picamera2 init failed: %s", self.index, exc)
            return False

    def _read_opencv(self, cap: cv2.VideoCapture | None):
        if cap is None or not cap.isOpened():
            return None
        ok, frame = cap.read()
        if not ok:
            self._consecutive_failures += 1
            if self._consecutive_failures % _FAIL_LOG_EVERY == 1:
                logger.warning(
                    "Camera read failed (consecutive failures: %d).",
                    self._consecutive_failures,
                )
            time.sleep(0.05)
            return None
        self._consecutive_failures = 0
        return frame

    def _read_picamera2(self, picam2):
        try:
            frame = picam2.capture_array()  # RGB888
            if frame is None:
                return None
            self._consecutive_failures = 0
            return frame[:, :, ::-1]  # RGB → BGR for OpenCV/YOLO
        except Exception as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures % _FAIL_LOG_EVERY == 1:
                logger.warning("picamera2 read failed: %s", exc)
            return None
