from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger("vision-v1.action")


class ActionService:
    """
    Scores actions from pose keypoints already computed by the Detector.
    No model loading — reads detector.get_latest_poses() each call.
    """

    def __init__(self, detector, enabled: bool = True) -> None:
        self.detector = detector
        self.enabled = bool(enabled)
        self.backend = "pose_detector" if self.enabled else "disabled"
        self.load_error: str | None = None if self.enabled else "disabled_by_config"
        self._prev_center: tuple[float, float] | None = None
        self._last_result: dict[str, Any] | None = None
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def get_last(self) -> dict[str, Any] | None:
        return dict(self._last_result) if self._last_result else None

    @staticmethod
    def _clip01(v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    def _get_kp(
        self, keypoints: list[dict], idx: int, min_conf: float = 0.2
    ) -> tuple[float, float] | None:
        if idx >= len(keypoints):
            return None
        kp = keypoints[idx]
        if (kp.get("confidence") or 0.0) < min_conf:
            return None
        return float(kp.get("x", 0.0)), float(kp.get("y", 0.0))

    def _score_from_poses(self, poses: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not poses:
            return None

        best_pose = max(poses, key=lambda p: p.get("confidence", 0.0))
        bbox = best_pose.get("bbox", [])   # [x, y, w, h]
        keypoints: list[dict] = best_pose.get("keypoints", [])

        # Center and scale from bounding box
        center: tuple[float, float] | None = None
        area = 0.0
        if len(bbox) == 4:
            x, y, w, h = bbox
            center = (x + w / 2.0, y + h / 2.0)
            area = max(1.0, float(w) * float(h))

        # Movement — normalized pixel delta between consecutive frames
        movement = 0.0
        if center is not None and self._prev_center is not None:
            dx = center[0] - self._prev_center[0]
            dy = center[1] - self._prev_center[1]
            dist = math.sqrt(dx * dx + dy * dy)
            scale = math.sqrt(area) + 1e-6
            movement = self._clip01(dist / (0.3 * scale))
        if center is not None:
            self._prev_center = center

        # COCO keypoint indices used below:
        # 5=left_shoulder  6=right_shoulder
        # 9=left_wrist    10=right_wrist
        # 11=left_hip     12=right_hip
        # 13=left_knee    14=right_knee

        # Hand raised: wrist above shoulder (lower image-y than shoulder)
        hand_raised = 0.0
        ls = self._get_kp(keypoints, 5)
        rs = self._get_kp(keypoints, 6)
        lw = self._get_kp(keypoints, 9)
        rw = self._get_kp(keypoints, 10)
        if lw and ls:
            hand_raised = max(hand_raised, self._clip01((ls[1] - lw[1]) / 50.0))
        if rw and rs:
            hand_raised = max(hand_raised, self._clip01((rs[1] - rw[1]) / 50.0))

        # Bending: compressed torso vs leg ratio
        bending = 0.0
        lh = self._get_kp(keypoints, 11)
        rh = self._get_kp(keypoints, 12)
        lk = self._get_kp(keypoints, 13)
        rk = self._get_kp(keypoints, 14)

        shoulders_y = ((ls[1] + rs[1]) / 2) if (ls and rs) else (ls[1] if ls else (rs[1] if rs else None))
        hips_y      = ((lh[1] + rh[1]) / 2) if (lh and rh) else (lh[1] if lh else (rh[1] if rh else None))
        knees_y     = ((lk[1] + rk[1]) / 2) if (lk and rk) else (lk[1] if lk else (rk[1] if rk else None))

        if shoulders_y is not None and hips_y is not None and knees_y is not None:
            torso = abs(hips_y - shoulders_y) + 1e-6
            leg   = abs(knees_y - hips_y) + 1e-6
            bending = self._clip01((0.85 - torso / leg) / 0.5)

        standing = self._clip01(1.0 - max(movement, hand_raised, bending))

        candidates = [
            {"label": "moving",      "score": round(movement,    3)},
            {"label": "hand_raised", "score": round(hand_raised, 3)},
            {"label": "bending",     "score": round(bending,     3)},
            {"label": "standing",    "score": round(standing,    3)},
        ]
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return {"best": candidates[0], "topk": candidates[:3]}

    def run_once(self) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        poses = self.detector.get_latest_poses()
        if not poses:
            return None
        return self._score_from_poses(poses)
