from __future__ import annotations

import logging
import math
import os
import time
from typing import Any

import cv2
import numpy as np
import requests
import torch
from torchvision.models.video import R2Plus1D_18_Weights, r2plus1d_18
from ultralytics import YOLO

logger = logging.getLogger("vision-v1.action")


class ActionService:
    def __init__(
        self,
        detector,
        interval_s: int,
        window_s: float,
        frames: int,
        use_gpu: bool,
        model_path: str | None = None,
        model_url: str | None = None,
    ) -> None:
        self.detector = detector
        self.interval_s = max(5, int(interval_s))
        self.window_s = max(0.5, float(window_s))
        self.frames = max(8, int(frames))
        self.device = torch.device("cuda" if use_gpu and torch.cuda.is_available() else "cpu")
        self.action_model_path = (model_path or "").strip() or None
        self.action_model_url = (model_url or "").strip() or None
        self.backend = "r2plus1d"

        self._pose_model = None
        self._weights = None
        self._model = None
        self._preprocess = None
        self._categories = None

        if self.action_model_path:
            try:
                resolved_path = self._resolve_model_path(self.action_model_path, self.action_model_url)
                self._pose_model = YOLO(resolved_path)
                self._pose_model.to(str(self.device))
                self.action_model_path = resolved_path
                self.backend = "yolo_pose"
                logger.info("Action backend set to yolo_pose with model: %s", resolved_path)
            except Exception as exc:
                if "Can't get attribute 'Pose26'" in str(exc):
                    logger.error(
                        "Action pose model requires newer ultralytics. Upgrade to >=8.4.0 to load yolo26n-pose.pt."
                    )
                logger.warning("Failed to initialize YOLO pose action backend: %s. Falling back to r2plus1d.", exc)

        if self.backend == "r2plus1d":
            try:
                self._weights = R2Plus1D_18_Weights.DEFAULT
                self._model = r2plus1d_18(weights=self._weights).to(self.device)
                self._model.eval()
                self._preprocess = self._weights.transforms()
                self._categories = self._weights.meta["categories"]
            except Exception as exc:
                logger.warning(
                    "Failed to initialize r2plus1d action backend (likely offline weights fetch issue): %s. "
                    "Action service disabled.",
                    exc,
                )
                self.backend = "disabled"
                self._weights = None
                self._model = None
                self._preprocess = None
                self._categories = None

        self._stop = False
        self._last_result: dict[str, Any] | None = None

    @staticmethod
    def _is_remote(path: str) -> bool:
        return path.startswith(("http://", "https://"))

    def _resolve_model_path(self, model_path: str, model_url: str | None) -> str:
        if self._is_remote(model_path):
            return model_path
        local_path = os.path.abspath(model_path)
        if os.path.exists(local_path):
            return local_path
        if not model_url:
            raise FileNotFoundError(f"Action model missing and ACTION_MODEL_URL is not set: {local_path}")
        return self._download_model(local_path, model_url)

    @staticmethod
    def _download_model(target_path: str, model_url: str) -> str:
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        tmp_path = f"{target_path}.part"
        logger.info("Downloading action model from %s to %s", model_url, target_path)
        try:
            with requests.get(model_url, stream=True, timeout=(15, 120)) as resp:
                resp.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
            os.replace(tmp_path, target_path)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise
        return target_path

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

    @staticmethod
    def _clip01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _mean_point(points: np.ndarray, indices: list[int]) -> tuple[float, float] | None:
        valid = [i for i in indices if i < points.shape[0]]
        if not valid:
            return None
        sub = points[valid]
        return float(np.mean(sub[:, 0])), float(np.mean(sub[:, 1]))

    def _run_pose_action(self, clip_rgb: np.ndarray) -> dict[str, Any] | None:
        if self._pose_model is None:
            return None
        frames_bgr = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in clip_rgb]
        results = self._pose_model.predict(
            source=frames_bgr,
            verbose=False,
            device=str(self.device),
            imgsz=640,
            conf=0.25,
        )
        if not results:
            return None

        centers: list[tuple[float, float]] = []
        areas: list[float] = []
        hand_raise_scores: list[float] = []
        bend_scores: list[float] = []

        for result in results:
            boxes = result.boxes
            if boxes is None or len(boxes) == 0:
                continue
            idx = int(torch.argmax(boxes.conf).item())
            box = boxes[idx]
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
            centers.append(((x1 + x2) * 0.5, (y1 + y2) * 0.5))
            areas.append(max(1.0, (x2 - x1) * (y2 - y1)))

            kp_block = getattr(result, "keypoints", None)
            if kp_block is None or len(kp_block.xy) <= idx:
                hand_raise_scores.append(0.0)
                bend_scores.append(0.0)
                continue

            pts = kp_block.xy[idx].cpu().numpy()
            left_shoulder = self._mean_point(pts, [5])
            right_shoulder = self._mean_point(pts, [6])
            left_wrist = self._mean_point(pts, [9])
            right_wrist = self._mean_point(pts, [10])
            shoulders = self._mean_point(pts, [5, 6])
            hips = self._mean_point(pts, [11, 12])
            knees = self._mean_point(pts, [13, 14])

            raise_score = 0.0
            if left_wrist and left_shoulder:
                raise_score = max(raise_score, self._clip01((left_shoulder[1] - left_wrist[1]) / 50.0))
            if right_wrist and right_shoulder:
                raise_score = max(raise_score, self._clip01((right_shoulder[1] - right_wrist[1]) / 50.0))
            hand_raise_scores.append(raise_score)

            if shoulders and hips and knees:
                torso = abs(hips[1] - shoulders[1]) + 1e-6
                leg = abs(knees[1] - hips[1]) + 1e-6
                ratio = torso / leg
                bend_scores.append(self._clip01((0.85 - ratio) / 0.5))
            else:
                bend_scores.append(0.0)

        if not centers:
            return None

        movement = 0.0
        if len(centers) >= 2:
            dx = centers[-1][0] - centers[0][0]
            dy = centers[-1][1] - centers[0][1]
            distance = math.sqrt(dx * dx + dy * dy)
            scale = math.sqrt(float(np.mean(areas))) + 1e-6
            movement = self._clip01(distance / (0.45 * scale))

        hand_raised = float(max(hand_raise_scores) if hand_raise_scores else 0.0)
        bending = float(max(bend_scores) if bend_scores else 0.0)
        standing = self._clip01(1.0 - max(movement, hand_raised, bending))

        candidates = [
            {"label": "moving", "score": movement},
            {"label": "hand_raised", "score": hand_raised},
            {"label": "bending", "score": bending},
            {"label": "standing", "score": standing},
        ]
        candidates.sort(key=lambda item: item["score"], reverse=True)
        topk = candidates[:3]
        best = topk[0] if topk else None
        return {"best": best, "topk": topk}

    def _run_video_classifier(self, clip_rgb: np.ndarray) -> dict[str, Any] | None:
        if self._model is None or self._preprocess is None or self._categories is None:
            return None
        video = torch.from_numpy(clip_rgb).permute(0, 3, 1, 2)  # T, C, H, W
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

    def run_once(self) -> dict[str, Any] | None:
        clip = self._capture_clip()
        if clip is None:
            return None
        if self.backend == "yolo_pose":
            return self._run_pose_action(clip)
        if self.backend == "r2plus1d":
            return self._run_video_classifier(clip)
        return None
