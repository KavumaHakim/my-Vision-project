from __future__ import annotations

import cv2
import threading
import time


class Camera:
    def __init__(self, index: int = 0) -> None:
        self.index = index
        self._source: int | str = index
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()

    def get_source(self) -> int | str:
        with self._lock:
            return self._source

    def set_source(self, source: int | str) -> None:
        with self._lock:
            self._source = source
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def open(self) -> None:
        with self._lock:
            if self._cap is not None and self._cap.isOpened():
                return
            cap = cv2.VideoCapture(self._source)
            if not cap.isOpened():
                cap.release()
                raise RuntimeError("Failed to open camera")
            self._cap = cap

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
