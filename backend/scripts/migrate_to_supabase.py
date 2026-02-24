import json
import os
import sqlite3

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


SQLITE_PATH = os.getenv("SQLITE_PATH", "faces.db")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def _to_bytea_hex(blob: bytes) -> str:
    return "\\x" + blob.hex()


def _load_faces(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute("SELECT id, name, embedding, dim, created_at FROM faces ORDER BY id")
    rows = cur.fetchall()
    results = []
    for row in rows:
        results.append(
            {
                "id": row[0],
                "name": row[1],
                "embedding": _to_bytea_hex(row[2]),
                "dim": row[3],
                "created_at": row[4],
            }
        )
    return results


def _load_events(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.execute(
        "SELECT id, event_type, face_type, face_id, name, score, bbox, created_at FROM events ORDER BY id"
    )
    rows = cur.fetchall()
    results = []
    for row in rows:
        bbox = None
        if row[6]:
            try:
                bbox = json.loads(row[6])
            except json.JSONDecodeError:
                bbox = None
        results.append(
            {
                "id": row[0],
                "event_type": row[1],
                "face_type": row[2],
                "face_id": row[3],
                "name": row[4],
                "score": row[5],
                "bbox": bbox,
                "created_at": row[7],
            }
        )
    return results


def _chunk(items, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def main() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

    conn = sqlite3.connect(SQLITE_PATH)
    faces = _load_faces(conn)
    events = _load_events(conn)
    conn.close()

    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    for batch in _chunk(faces, 200):
        client.table("faces").upsert(batch).execute()

    for batch in _chunk(events, 500):
        client.table("events").upsert(batch).execute()

    print(f"Migrated faces: {len(faces)}")
    print(f"Migrated events: {len(events)}")


if __name__ == "__main__":
    main()
