from __future__ import annotations

import logging
import os
import threading
import time
from typing import Generator, Optional

import cv2
import numpy as np

from utils import ensure_dir, timestamp_str

logger = logging.getLogger("vision-v1.camera_streamer")


class CameraStreamer:
    """
    Single owner of the camera. One thread captures raw frames at a target FPS
    and publishes the latest frame to every consumer (the detector, the smooth
    MJPEG stream, and the recorder), so heavy inference never throttles capture.

    Without this, the detector read the camera directly and the whole feed ran
    at inference speed (~5-10 FPS, choppy). Here capture stays smooth (~25 FPS)
    regardless of how slow inference is.
    """

    def __init__(self, camera, target_fps: int = 25, recordings_dir: str = "recordings") -> None:
        self.camera = camera
        self.target_fps = max(1, int(target_fps))
        self.recordings_dir = recordings_dir
        self._frame_interval = 1.0 / self.target_fps

        self._lock = threading.Lock()
        self._latest: Optional[np.ndarray] = None
        self._latest_ts = 0.0
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Recording state (separate lock so a slow write never blocks readers).
        self._rec_lock = threading.Lock()
        self._writer: Optional[cv2.VideoWriter] = None
        self._rec_path: Optional[str] = None
        self._rec_started_at = 0.0
        self._rec_frames = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self.stop_recording()

    def _loop(self) -> None:
        next_t = time.time()
        while not self._stop.is_set():
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.02)
                continue

            with self._lock:
                self._latest = frame
                self._latest_ts = time.time()

            with self._rec_lock:
                if self._writer is not None:
                    try:
                        self._writer.write(frame)
                        self._rec_frames += 1
                    except Exception:
                        logger.exception("Recording write failed; stopping recorder.")
                        self._close_writer_locked()

            # Pace to the target FPS so capture is smooth and CPU stays sane.
            next_t += self._frame_interval
            sleep = next_t - time.time()
            if sleep > 0:
                time.sleep(sleep)
            else:
                next_t = time.time()

    # ------------------------------------------------------------------
    # Frame access
    # ------------------------------------------------------------------
    def read_latest(self) -> Optional[np.ndarray]:
        """Frame source for the detector — the most recent raw frame (a copy)."""
        with self._lock:
            return None if self._latest is None else self._latest.copy()

    def mjpeg(self, fps: Optional[int] = None, annotate=None) -> Generator[bytes, None, None]:
        """Smooth MJPEG stream of the raw camera.

        If ``annotate`` is given, it is called with each frame before encoding
        (e.g. to draw the latest detection boxes) — smooth motion plus boxes.
        """
        delay = 1.0 / max(1, int(fps or self.target_fps))
        while True:
            frame = self.read_latest()
            if frame is None:
                time.sleep(0.05)
                continue
            if annotate is not None:
                try:
                    annotate(frame)
                except Exception:
                    logger.exception("Smooth-stream overlay failed; sending raw frame.")
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                time.sleep(delay)
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
            )
            time.sleep(delay)

    # ------------------------------------------------------------------
    # Recording (manual on/off, raw frames, local disk)
    # ------------------------------------------------------------------
    def start_recording(self) -> dict:
        with self._rec_lock:
            if self._writer is not None:
                return {"ok": True, "recording": True, "path": self._rec_path, "already": True}
            frame = self.read_latest()
            if frame is None:
                return {"ok": False, "error": "no_frame"}
            h, w = frame.shape[:2]
            ensure_dir(self.recordings_dir)
            filename = f"rec_{timestamp_str()}.mp4"
            path = os.path.join(self.recordings_dir, filename)
            writer = cv2.VideoWriter(
                path, cv2.VideoWriter_fourcc(*"mp4v"), float(self.target_fps), (w, h)
            )
            if not writer.isOpened():
                try:
                    writer.release()
                except Exception:
                    pass
                return {"ok": False, "error": "writer_open_failed"}
            self._writer = writer
            self._rec_path = path
            self._rec_started_at = time.time()
            self._rec_frames = 0
            logger.info("Recording started: %s", path)
            return {"ok": True, "recording": True, "path": path}

    def stop_recording(self) -> dict:
        with self._rec_lock:
            if self._writer is None:
                return {"ok": True, "recording": False}
            path = self._rec_path
            frames = self._rec_frames
            self._close_writer_locked()
            logger.info("Recording stopped: %s (%d frames)", path, frames)
            return {"ok": True, "recording": False, "path": path, "frames": frames}

    def _close_writer_locked(self) -> None:
        if self._writer is not None:
            try:
                self._writer.release()
            except Exception:
                pass
        self._writer = None
        self._rec_path = None

    def recording_status(self) -> dict:
        with self._rec_lock:
            recording = self._writer is not None
            return {
                "recording": recording,
                "path": os.path.basename(self._rec_path) if self._rec_path else None,
                "frames": self._rec_frames if recording else 0,
                "duration_s": round(time.time() - self._rec_started_at, 1) if recording else 0.0,
                "target_fps": self.target_fps,
            }
