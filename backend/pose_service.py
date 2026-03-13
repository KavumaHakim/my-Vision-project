from __future__ import annotations

import logging
import math
import os
import time
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
        self._track_state: dict[int, dict[str, float]] = {}
        self._next_track_id = 1
        self._track_ttl_s = 3.0

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

    def _match_track_ids(
        self,
        centers: list[tuple[float, float]],
        areas: list[float],
        now_ts: float,
    ) -> list[int]:
        stale = [track_id for track_id, state in self._track_state.items() if now_ts - state["last_seen"] > self._track_ttl_s]
        for track_id in stale:
            self._track_state.pop(track_id, None)

        assignments: list[int] = [-1] * len(centers)
        used_tracks: set[int] = set()
        order = sorted(range(len(centers)), key=lambda i: areas[i], reverse=True)
        for idx in order:
            cx, cy = centers[idx]
            area = max(1.0, float(areas[idx]))
            best_track_id: int | None = None
            best_score = float("inf")
            for track_id, state in self._track_state.items():
                if track_id in used_tracks:
                    continue
                prev_cx, prev_cy = state["cx"], state["cy"]
                prev_area = max(1.0, float(state["area"]))
                scale = math.sqrt(max(prev_area, area)) + 1e-6
                distance = math.hypot(cx - prev_cx, cy - prev_cy)
                norm_distance = distance / (0.6 * scale)
                if norm_distance < best_score:
                    best_score = norm_distance
                    best_track_id = track_id
            if best_track_id is not None and best_score <= 1.0:
                assignments[idx] = best_track_id
                used_tracks.add(best_track_id)
                continue
            track_id = self._next_track_id
            self._next_track_id += 1
            assignments[idx] = track_id
            used_tracks.add(track_id)
        return assignments

    def _infer_action(
        self,
        keypoints_xy: np.ndarray | None,
        bbox: list[int],
        previous_state: dict[str, float] | None,
    ) -> dict[str, Any]:
        x, y, w, h = bbox
        cx = float(x + w * 0.5)
        cy = float(y + h * 0.5)
        area = max(1.0, float(w * h))

        movement = 0.0
        if previous_state:
            prev_cx = float(previous_state["cx"])
            prev_cy = float(previous_state["cy"])
            prev_area = max(1.0, float(previous_state["area"]))
            scale = math.sqrt(max(area, prev_area)) + 1e-6
            movement = self._clip01(math.hypot(cx - prev_cx, cy - prev_cy) / (0.45 * scale))

        hand_raised = 0.0
        bending = 0.0
        if keypoints_xy is not None and keypoints_xy.shape[0] > 0:
            left_shoulder = self._mean_point(keypoints_xy, [5])
            right_shoulder = self._mean_point(keypoints_xy, [6])
            left_wrist = self._mean_point(keypoints_xy, [9])
            right_wrist = self._mean_point(keypoints_xy, [10])
            shoulders = self._mean_point(keypoints_xy, [5, 6])
            hips = self._mean_point(keypoints_xy, [11, 12])
            knees = self._mean_point(keypoints_xy, [13, 14])

            if left_wrist and left_shoulder:
                hand_raised = max(hand_raised, self._clip01((left_shoulder[1] - left_wrist[1]) / 50.0))
            if right_wrist and right_shoulder:
                hand_raised = max(hand_raised, self._clip01((right_shoulder[1] - right_wrist[1]) / 50.0))
            if shoulders and hips and knees:
                torso = abs(hips[1] - shoulders[1]) + 1e-6
                leg = abs(knees[1] - hips[1]) + 1e-6
                ratio = torso / leg
                bending = self._clip01((0.85 - ratio) / 0.5)

        standing = self._clip01(1.0 - max(movement, hand_raised, bending))
        candidates = [
            {"label": "moving", "score": movement},
            {"label": "hand_raised", "score": hand_raised},
            {"label": "bending", "score": bending},
            {"label": "standing", "score": standing},
        ]
        candidates.sort(key=lambda item: item["score"], reverse=True)
        best = candidates[0] if candidates else None
        return {"best": best, "topk": candidates[:3]}

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
        raw_xy: list[np.ndarray | None] = []
        centers: list[tuple[float, float]] = []
        areas: list[float] = []
        for idx, box in enumerate(boxes):
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            x1, y1, x2, y2 = xyxy
            conf = float(box.conf[0].cpu().item())
            w = int(max(0, x2 - x1))
            h = int(max(0, y2 - y1))
            pose_item: dict[str, Any] = {
                "confidence": conf,
                "bbox": [int(x1), int(y1), w, h],
                "keypoints": [],
            }
            xy = None
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
            raw_xy.append(xy)
            centers.append((float(x1 + x2) * 0.5, float(y1 + y2) * 0.5))
            areas.append(max(1.0, float(w * h)))

        now_ts = time.time()
        track_ids = self._match_track_ids(centers, areas, now_ts)
        action_items: list[dict[str, Any]] = []
        for idx, pose_item in enumerate(poses):
            track_id = track_ids[idx]
            previous = self._track_state.get(track_id)
            action_result = self._infer_action(raw_xy[idx], pose_item["bbox"], previous)
            best = action_result.get("best")
            pose_item["track_id"] = track_id
            pose_item["action"] = best
            pose_item["action_topk"] = action_result.get("topk", [])
            if best:
                action_items.append({"track_id": track_id, "label": best["label"], "score": float(best["score"])})

            x, y, w, h = pose_item["bbox"]
            self._track_state[track_id] = {
                "cx": float(x + w * 0.5),
                "cy": float(y + h * 0.5),
                "area": max(1.0, float(w * h)),
                "last_seen": now_ts,
            }

        best_action = max(action_items, key=lambda item: float(item.get("score", 0.0)), default=None)
        return {"poses": poses, "actions": action_items, "best_action": best_action}
