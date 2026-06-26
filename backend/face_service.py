from __future__ import annotations

from typing import Any

import numpy as np


class FaceService:
    def __init__(self, model_name: str, use_gpu: bool, enabled: bool = True) -> None:
        self.enabled = bool(enabled)
        self.load_error: str | None = None
        self._app = None
        if not self.enabled:
            self.load_error = "disabled_by_config"
            return
        try:
            from insightface.app import FaceAnalysis
        except Exception as exc:
            self.enabled = False
            self.load_error = f"insightface_import_failed: {exc}"
            return
        providers = ["CPUExecutionProvider"]
        if use_gpu:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        try:
            self._app = FaceAnalysis(name=model_name, providers=providers)
            self._app.prepare(ctx_id=0 if use_gpu else -1, det_size=(640, 640))
        except Exception as exc:
            self.enabled = False
            self._app = None
            self.load_error = f"face_model_init_failed: {exc}"

    def get_faces(self, image_bgr: np.ndarray) -> list[dict[str, Any]]:
        if not self.enabled or self._app is None:
            return []
        faces = self._app.get(image_bgr)
        results: list[dict[str, Any]] = []
        for face in faces:
            results.append(
                {
                    "bbox": [float(v) for v in face.bbox],
                    "embedding": face.embedding,
                }
            )
        return results

    def get_embedding(self, image_bgr: np.ndarray) -> tuple[np.ndarray | None, dict[str, Any]]:
        if not self.enabled or self._app is None:
            return None, {"error": "face_service_disabled", "detail": self.load_error}
        faces = self._app.get(image_bgr)
        if not faces:
            return None, {"error": "no_face"}
        face = max(
            faces,
            key=lambda f: (float(f.bbox[2]) - float(f.bbox[0]))
            * (float(f.bbox[3]) - float(f.bbox[1])),
        )
        return face.embedding, {"bbox": [float(v) for v in face.bbox], "faces": len(faces)}
