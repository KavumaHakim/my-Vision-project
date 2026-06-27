from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Generator

import cv2


def _result_age_s(result) -> float | None:
    """Seconds since the recognition result was produced, or None if unknown."""
    ts = result.get("timestamp")
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(ts)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - parsed).total_seconds()


def _draw_face_label(frame, result, max_age_s: float) -> None:
    if not result or not result.get("ok"):
        return
    # Drop the overlay once the result goes stale. The recognition loop only
    # refreshes the timestamp while a subject is present, so after they leave
    # the box ages out instead of lingering — but it stays visible between
    # recognition cycles (and through brief stillness) while they're here.
    age = _result_age_s(result)
    if age is not None and age > max_age_s:
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


def unified_stream(
    detector,
    camera_streamer,
    face_recognition_service,
    mode_getter,
    inference_fps: int = 10,
    smooth_fps: int = 25,
) -> Generator[bytes, None, None]:
    """One persistent MJPEG stream whose content follows ``mode_getter()``.

    Switching modes server-side means the client never reconnects (no
    "reconnecting" flash). Modes:
      - "inference"  : the annotated inference frame (boxes synced, ~choppy)
      - "smooth"     : raw ~smooth_fps frame + latest boxes/face overlaid
      - "smooth_raw" : raw ~smooth_fps frame, no overlays
    """
    overlay_ttl = float(getattr(face_recognition_service, "interval_s", 10)) + 5.0

    while True:
        mode = mode_getter()
        if mode == "inference":
            frame = detector.get_latest_frame(annotated=True)
            delay = 1.0 / max(1, inference_fps)
            draw_boxes = False  # the annotated frame already has them
            draw_face = True
        else:
            frame = camera_streamer.read_latest()
            delay = 1.0 / max(1, smooth_fps)
            draw_boxes = mode == "smooth"
            draw_face = mode == "smooth"

        if frame is None:
            time.sleep(0.05)
            continue
        if draw_boxes:
            detector.draw_latest_overlays(frame)
        if draw_face and face_recognition_service is not None:
            _draw_face_label(frame, face_recognition_service.get_last(), overlay_ttl)

        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            time.sleep(delay)
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
        )
        time.sleep(delay)


def mjpeg_generator(detector, fps: int, face_recognition_service=None) -> Generator[bytes, None, None]:
    delay = 1.0 / max(1, fps)
    # Keep the face box through the gap between recognition cycles, then clear
    # it shortly after the subject leaves. TTL = one recognition interval plus a
    # margin so it never flickers off right before the next cycle.
    overlay_ttl = 15.0
    if face_recognition_service is not None:
        overlay_ttl = float(getattr(face_recognition_service, "interval_s", 10)) + 5.0
    while True:
        frame = detector.get_latest_frame(annotated=True)
        if frame is None:
            time.sleep(0.05)
            continue
        if face_recognition_service is not None:
            _draw_face_label(frame, face_recognition_service.get_last(), overlay_ttl)
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
