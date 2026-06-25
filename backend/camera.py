from __future__ import annotations

import cv2
import threading
import time


class Camera:
    def __init__(self, index: int = 0, width: int = 640, height: int = 480) -> None:
        self.index = index
        self.width = width
        self.height = height
        self._source: int | str = index
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()
        self._latest_frame = None
        self._running = False
        self._thread: threading.Thread | None = None

    def get_source(self) -> int | str:
        with self._lock:
            return self._source

    def set_source(self, source: int | str) -> None:
        with self._lock:
            self._source = source
            self._stop_thread()
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
            
            # Apply resolution configuration
            if isinstance(self._source, int):
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            self._cap = cap
            self._latest_frame = None
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()

    def close(self) -> None:
        with self._lock:
            self._stop_thread()
            if self._cap is not None:
                self._cap.release()
                self._cap = None

    def _stop_thread(self) -> None:
        self._running = False

    def _capture_loop(self) -> None:
        while True:
            with self._lock:
                if not self._running or self._cap is None or not self._cap.isOpened():
                    break
                cap = self._cap
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            with self._lock:
                self._latest_frame = frame
            time.sleep(0.005)

    def is_opened(self) -> bool:
        with self._lock:
            return self._cap is not None and self._cap.isOpened() and self._running

    def read(self):
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

