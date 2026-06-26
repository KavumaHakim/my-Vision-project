from __future__ import annotations

import cv2
import threading
import time


class Camera:
    def __init__(self, index: int = 0, backend: int | None = None) -> None:
        self.index = index
        self.backend = backend
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()

    def open(self, timeout_s: float = 5.0) -> None:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                return

        result: dict[str, cv2.VideoCapture | Exception | None] = {"cap": None, "error": None}

        def _open_worker() -> None:
            try:
                if self.backend is None:
                    cap = cv2.VideoCapture(self.index)
                else:
                    cap = cv2.VideoCapture(self.index, self.backend)
                if not cap.isOpened():
                    cap.release()
                    result["error"] = RuntimeError("Failed to open camera")
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
            err = result["error"]
            if isinstance(err, Exception):
                raise RuntimeError(str(err))
            raise RuntimeError("Failed to open camera")

        cap = result["cap"]
        if cap is None:
            raise RuntimeError("Failed to open camera")
        with self._lock:
            if self._cap is None:
                self._cap = cap
            else:
                cap.release()

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
            time.sleep(0.05)
            return None
        return frame
