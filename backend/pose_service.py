from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np
import requests
from ultralytics import YOLO

logger = logging.getLogger("vision-v1.pose")


class PoseService:
    def __init__(self, model_path: str | None, model_url: str | None, use_gpu: bool) -> None:
        self.model_path = (model_path or "").strip()
        self.model_url = (model_url or "").strip() or None
        self.enabled = bool(self.model_path)
        self.device = "cuda" if use_gpu else "cpu"
        self.backend = "disabled"
        self.load_error: str | None = None
        self._model = None
        if self.enabled:
            try:
                resolved_path = self._resolve_model_path(self.model_path, self.model_url)
                self._model = YOLO(resolved_path)
                self._model.to(self.device)
                self.model_path = resolved_path
                self.backend = "yolo_pose"
            except Exception as exc:
                self.enabled = False
                self._model = None
                self.backend = "disabled"
                self.load_error = str(exc)
                if "Can't get attribute 'Pose26'" in self.load_error:
                    logger.error(
                        "Pose model requires newer ultralytics. Upgrade to >=8.4.0 to load yolo26n-pose.pt."
                    )
                logger.warning("Pose service disabled because model init failed: %s", exc)

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
            raise FileNotFoundError(f"Pose model missing and POSE_MODEL_URL is not set: {local_path}")
        return self._download_model(local_path, model_url)

    @staticmethod
    def _download_model(target_path: str, model_url: str) -> str:
        os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
        tmp_path = f"{target_path}.part"
        logger.info("Downloading pose model from %s to %s", model_url, target_path)
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

    def run_once(self, frame: np.ndarray, conf_threshold: float = 0.25) -> dict[str, Any] | None:
        if not self.enabled or self._model is None:
            return None
        results = self._model.predict(
            source=frame,
            verbose=False,
            device=self.device,
            imgsz=640,
            conf=float(conf_threshold),
        )
        if not results:
            return {"poses": []}
        result = results[0]
        poses: list[dict[str, Any]] = []
        keypoints = getattr(result, "keypoints", None)
        boxes = result.boxes or []
        for idx, box in enumerate(boxes):
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            x1, y1, x2, y2 = xyxy
            conf = float(box.conf[0].cpu().item())
            pose_item: dict[str, Any] = {
                "confidence": conf,
                "bbox": [int(x1), int(y1), int(max(0, x2 - x1)), int(max(0, y2 - y1))],
                "keypoints": [],
            }
            if keypoints is not None and len(keypoints.xy) > idx:
                xy = keypoints.xy[idx].cpu().numpy()
                kp_conf = None
                if keypoints.conf is not None and len(keypoints.conf) > idx:
                    kp_conf = keypoints.conf[idx].cpu().numpy()
                points = []
                for j in range(xy.shape[0]):
                    score = float(kp_conf[j]) if kp_conf is not None else None
                    points.append(
                        {
                            "x": float(xy[j][0]),
                            "y": float(xy[j][1]),
                            "confidence": score,
                        }
                    )
                pose_item["keypoints"] = points
            poses.append(pose_item)
        return {"poses": poses}
