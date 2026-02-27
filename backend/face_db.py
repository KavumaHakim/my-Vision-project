from __future__ import annotations

import json
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
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS unknown_faces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    embedding BLOB NOT NULL,
                    dim INTEGER NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    sightings INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    face_type TEXT NOT NULL,
                    face_id INTEGER,
                    name TEXT,
                    score REAL,
                    bbox TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS face_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    face_id INTEGER NOT NULL,
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
            cur_samples = self._conn.execute(
                "SELECT face_id, embedding, dim FROM face_samples"
            )
            sample_rows = cur_samples.fetchall()
        id_to_name = {int(row["id"]): str(row["name"]) for row in rows}
        for row in rows:
            emb = np.frombuffer(row["embedding"], dtype=np.float32)
            if emb.size != row["dim"]:
                continue
            yield int(row["id"]), str(row["name"]), emb
        for row in sample_rows:
            emb = np.frombuffer(row["embedding"], dtype=np.float32)
            if emb.size != row["dim"]:
                continue
            face_id = int(row["face_id"])
            name = id_to_name.get(face_id, "unknown")
            yield face_id, name, emb

    def add_face_sample(self, face_id: int, embedding: np.ndarray) -> int:
        emb = np.asarray(embedding, dtype=np.float32)
        payload = emb.tobytes()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO face_samples (face_id, embedding, dim, created_at) VALUES (?, ?, ?, ?)",
                (face_id, payload, emb.size, datetime.utcnow().isoformat()),
            )
            return int(cur.lastrowid)

    def iter_unknown_embeddings(self) -> Iterable[tuple[int, np.ndarray]]:
        with self._lock:
            cur = self._conn.execute("SELECT id, embedding, dim FROM unknown_faces")
            rows = cur.fetchall()
        for row in rows:
            emb = np.frombuffer(row["embedding"], dtype=np.float32)
            if emb.size != row["dim"]:
                continue
            yield int(row["id"]), emb

    def update_unknown(self, unknown_id: int, embedding: np.ndarray) -> None:
        emb = np.asarray(embedding, dtype=np.float32)
        payload = emb.tobytes()
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE unknown_faces SET embedding = ?, dim = ?, last_seen = ?, sightings = sightings + 1 WHERE id = ?",
                (payload, emb.size, datetime.utcnow().isoformat(), unknown_id),
            )

    def add_unknown(self, embedding: np.ndarray) -> int:
        emb = np.asarray(embedding, dtype=np.float32)
        payload = emb.tobytes()
        now = datetime.utcnow().isoformat()
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO unknown_faces (embedding, dim, first_seen, last_seen, sightings) VALUES (?, ?, ?, ?, 1)",
                (payload, emb.size, now, now),
            )
            return int(cur.lastrowid)

    def add_event(
        self,
        event_type: str,
        face_type: str,
        face_id: int | None,
        name: str | None,
        score: float | None,
        bbox: list[float] | None,
    ) -> None:
        payload = json.dumps(bbox) if bbox else None
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO events (event_type, face_type, face_id, name, score, bbox, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    face_type,
                    face_id,
                    name,
                    score,
                    payload,
                    datetime.utcnow().isoformat(),
                ),
            )

    def list_events(self, limit: int = 100) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT id, event_type, face_type, face_id, name, score, bbox, created_at
                FROM events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
        results = []
        for row in rows:
            item = dict(row)
            if item.get("bbox"):
                try:
                    item["bbox"] = json.loads(item["bbox"])
                except json.JSONDecodeError:
                    item["bbox"] = None
            results.append(item)
        return results

    def list_attendance(self, limit: int = 50) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT name,
                       COUNT(*) as total,
                       MAX(created_at) as last_seen
                FROM events
                WHERE event_type = 'face_recognized' AND face_type = 'known' AND name IS NOT NULL
                GROUP BY name
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [dict(row) for row in rows]
