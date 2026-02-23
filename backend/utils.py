from __future__ import annotations

import datetime as dt
import logging
import os


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def timestamp_str() -> str:
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def dated_path(root: str, timestamp: dt.datetime | None = None) -> str:
    ts = timestamp or now_utc()
    return os.path.join(root, ts.strftime("%Y"), ts.strftime("%m"), ts.strftime("%d"))


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
