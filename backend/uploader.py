from __future__ import annotations

import time
from typing import Any

from supabase import create_client

from utils import now_utc


class SupabaseUploader:
    def __init__(self, url: str | None, key: str | None, bucket: str = "captures") -> None:
        self.enabled = bool(url and key)
        self.bucket = bucket
        self._client = create_client(url, key) if self.enabled else None

    def upload_image(self, storage_path: str, data: bytes, content_type: str = "image/jpeg") -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "error": "Supabase not configured"}

        bucket = self._client.storage.from_(self.bucket)
        last_error = None
        for attempt in range(4):
            try:
                bucket.upload(storage_path, data, {"content-type": content_type, "upsert": False})
                public_url = bucket.get_public_url(storage_path)
                return {"ok": True, "url": public_url}
            except Exception as exc:  # pragma: no cover - transient SDK errors
                last_error = str(exc)
                time.sleep(2**attempt)
        return {"ok": False, "error": last_error or "upload failed"}


def build_storage_path(filename: str) -> str:
    ts = now_utc()
    folder = ts.strftime("%Y/%m/%d")
    return f"{folder}/{filename}"
