from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from typing import Iterable

import numpy as np


class FaceDB:
    def __init__(self, path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS faces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    dim INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add(self, name: str, embedding: np.ndarray) -> int:
        emb = np.asarray(embedding, dtype=np.float32)
        payload = emb.tobytes()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO faces (name, embedding, dim, created_at) VALUES (?, ?, ?, ?)",
                (name, payload, emb.size, datetime.utcnow().isoformat()),
            )
            return int(cur.lastrowid)

    def list_names(self) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, name, created_at FROM faces ORDER BY id DESC"
            )
            return [dict(row) for row in cur.fetchall()]

    def iter_embeddings(self) -> Iterable[tuple[int, str, np.ndarray]]:
        with self._lock:
            cur = self._conn.execute("SELECT id, name, embedding, dim FROM faces")
            rows = cur.fetchall()
        for row in rows:
            emb = np.frombuffer(row["embedding"], dtype=np.float32)
            if emb.size != row["dim"]:
                continue
            yield int(row["id"]), str(row["name"]), emb
