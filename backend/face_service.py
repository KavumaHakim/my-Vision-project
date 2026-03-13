from __future__ import annotations

import logging
from typing import Any

import numpy as np
from insightface.app import FaceAnalysis

logger = logging.getLogger("vision-v1.face")


class FaceService:
    def __init__(self, model_name: str, use_gpu: bool) -> None:
        self.enabled = False
        self.load_error: str | None = None
        self._app = None
        providers = ["CPUExecutionProvider"]
        if use_gpu:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        try:
            self._app = FaceAnalysis(name=model_name, providers=providers)
            self._app.prepare(ctx_id=0 if use_gpu else -1, det_size=(640, 640))
            self.enabled = True
        except Exception as exc:
            self.load_error = str(exc)
            logger.warning("Face service unavailable at startup. Running without face model: %s", exc)

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
            return None, {"error": "face_service_unavailable", "detail": self.load_error}
        faces = self._app.get(image_bgr)
        if not faces:
            return None, {"error": "no_face"}
        face = max(
            faces,
            key=lambda f: (float(f.bbox[2]) - float(f.bbox[0]))
            * (float(f.bbox[3]) - float(f.bbox[1])),
        )
        return face.embedding, {"bbox": [float(v) for v in face.bbox], "faces": len(faces)}
