from __future__ import annotations

import time
from typing import Generator

import cv2


def _draw_face_label(frame, result) -> None:
    if not result or not result.get("ok"):
        return
    faces = result.get("faces") or []
    for face in faces:
        bbox = face.get("bbox")
        best = face.get("best")
        if not bbox or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = [int(v) for v in bbox]
        label = best["name"] if best else "unknown"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 128, 0), 2)
        cv2.putText(
            frame,
            label,
            (x1, max(0, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 128, 0),
            2,
            cv2.LINE_AA,
        )


def mjpeg_generator(detector, fps: int, face_recognition_service=None) -> Generator[bytes, None, None]:
    delay = 1.0 / max(1, fps)
    while True:
        frame = detector.get_latest_frame(annotated=True)
        if frame is None:
            time.sleep(0.05)
            continue
        if face_recognition_service is not None:
            _draw_face_label(frame, face_recognition_service.get_last())
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
