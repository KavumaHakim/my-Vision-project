from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np
import torch
from torchvision.models.video import R2Plus1D_18_Weights, r2plus1d_18


class ActionService:
    def __init__(
        self,
        detector,
        interval_s: int,
        window_s: float,
        frames: int,
        use_gpu: bool,
    ) -> None:
        self.detector = detector
        self.interval_s = max(5, int(interval_s))
        self.window_s = max(0.5, float(window_s))
        self.frames = max(8, int(frames))
        self.device = torch.device("cuda" if use_gpu and torch.cuda.is_available() else "cpu")

        self._weights = R2Plus1D_18_Weights.DEFAULT
        self._model = r2plus1d_18(weights=self._weights).to(self.device)
        self._model.eval()
        self._preprocess = self._weights.transforms()
        self._categories = self._weights.meta["categories"]

        self._stop = False
        self._last_result: dict[str, Any] | None = None

    def stop(self) -> None:
        self._stop = True

    def get_last(self) -> dict[str, Any] | None:
        return dict(self._last_result) if self._last_result else None

    def _capture_clip(self) -> np.ndarray | None:
        interval = self.window_s / self.frames
        frames = []
        for _ in range(self.frames):
            frame = self.detector.get_latest_frame(annotated=False)
            if frame is None:
                time.sleep(0.02)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(rgb)
            time.sleep(interval)
        if len(frames) < max(4, self.frames // 2):
            return None
        return np.stack(frames, axis=0)

    def run_once(self) -> dict[str, Any] | None:
        clip = self._capture_clip()
        if clip is None:
            return None
        video = torch.from_numpy(clip).permute(0, 3, 1, 2)  # T, C, H, W
        video = self._preprocess(video).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self._model(video).squeeze(0)
            probs = torch.softmax(logits, dim=0)
        topk = torch.topk(probs, k=3)
        results = []
        for score, idx in zip(topk.values.cpu().tolist(), topk.indices.cpu().tolist()):
            results.append({"label": self._categories[idx], "score": float(score)})
        best = results[0] if results else None
        return {"best": best, "topk": results}
