from __future__ import annotations

from typing import Any

import numpy as np
from ultralytics import YOLO


class PoseService:
    def __init__(self, model_path: str | None, use_gpu: bool) -> None:
        self.model_path = (model_path or "").strip()
        self.enabled = bool(self.model_path)
        self.device = "cuda" if use_gpu else "cpu"
        self._model = None
        if self.enabled:
            self._model = YOLO(self.model_path)
            self._model.to(self.device)

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
