from __future__ import annotations

import io
import threading
import time
import wave
from typing import Any

import numpy as np
import requests
import sounddevice as sd


class AudioAlertService:
    def __init__(
        self,
        face_db,
        hf_url: str | None,
        hf_token: str | None,
        labels: list[str],
        threshold: float,
        interval_s: int,
        window_s: float,
        sample_rate: int,
        device: str | int | None,
        local_model: str | None,
    ) -> None:
        self.face_db = face_db
        self.hf_url = hf_url
        self.hf_token = hf_token
        self.labels = [label.lower() for label in labels]
        self.threshold = float(threshold)
        self.interval_s = max(2, int(interval_s))
        self.window_s = max(0.5, float(window_s))
        self.sample_rate = int(sample_rate)
        self.device = device
        self.local_model = local_model

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_result: dict[str, Any] | None = None
        self._local_pipeline = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def get_last(self) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._last_result) if self._last_result else None

    def _set_last(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._last_result = payload

    def _record_wav(self) -> bytes | None:
        frames = int(self.sample_rate * self.window_s)
        try:
            audio = sd.rec(
                frames,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.device,
            )
            sd.wait()
        except Exception:
            return None
        pcm = np.clip(audio.squeeze() * 32767.0, -32768, 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm.tobytes())
        return buf.getvalue()

    def _call_hf(self, wav_bytes: bytes) -> list[dict[str, Any]] | None:
        if not self.hf_url or not self.hf_token:
            return None
        headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Content-Type": "audio/wav",
        }
        try:
            resp = requests.post(self.hf_url, headers=headers, data=wav_bytes, timeout=30)
            data = resp.json()
        except Exception:
            return None
        if resp.status_code >= 400:
            return None
        if isinstance(data, list):
            return data
        return None

    def _call_local(self, wav_bytes: bytes) -> list[dict[str, Any]] | None:
        if not self.local_model:
            return None
        if self._local_pipeline is None:
            try:
                from transformers import pipeline
            except Exception:
                return None
            self._local_pipeline = pipeline("audio-classification", model=self.local_model)
        try:
            return self._local_pipeline(wav_bytes, top_k=5)
        except Exception:
            return None

    def _pick_alert(self, results: list[dict[str, Any]]) -> dict[str, Any] | None:
        best = None
        for item in results:
            label = str(item.get("label", "")).lower()
            score = float(item.get("score", 0.0))
            if label in self.labels and score >= self.threshold:
                if not best or score > best["score"]:
                    best = {"label": label, "score": score}
        return best

    def _loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self.interval_s)
            wav_bytes = self._record_wav()
            if not wav_bytes:
                continue
            results = self._call_hf(wav_bytes) or self._call_local(wav_bytes)
            if not results:
                self._set_last({"ok": False, "error": "no_results"})
                continue
            alert = self._pick_alert(results)
            if alert:
                self.face_db.add_event(
                    event_type="audio_alert",
                    face_type="audio",
                    face_id=None,
                    name=alert["label"],
                    score=alert["score"],
                    bbox=None,
                )
            self._set_last({"ok": True, "alert": alert, "results": results})
