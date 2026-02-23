from __future__ import annotations

import time
from typing import Generator

import cv2


def mjpeg_generator(detector, fps: int) -> Generator[bytes, None, None]:
    delay = 1.0 / max(1, fps)
    while True:
        frame = detector.get_latest_frame(annotated=True)
        if frame is None:
            time.sleep(0.05)
            continue
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            time.sleep(delay)
            continue
        payload = encoded.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"
        )
        time.sleep(delay)
