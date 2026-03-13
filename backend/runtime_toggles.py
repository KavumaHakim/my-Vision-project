from __future__ import annotations

import threading


class RuntimeModelToggles:
    DEFAULTS = {
        "object_detection": True,
        "face_recognition": True,
        "emotion": True,
        "action_tracking": True,
        "pose_tracking": True,
        "audio_alerts": True,
        "crowd_analysis": True,
    }

    def __init__(self, initial: dict[str, bool] | None = None) -> None:
        self._lock = threading.Lock()
        self._state = dict(self.DEFAULTS)
        if initial:
            self.set_many(initial)

    def get_all(self) -> dict[str, bool]:
        with self._lock:
            return dict(self._state)

    def is_enabled(self, key: str) -> bool:
        with self._lock:
            return bool(self._state.get(key, False))

    def set_many(self, updates: dict[str, bool]) -> dict[str, bool]:
        if not isinstance(updates, dict):
            raise TypeError("updates must be a dict")
        with self._lock:
            for key, value in updates.items():
                if key not in self._state:
                    raise KeyError(key)
                self._state[key] = bool(value)
            return dict(self._state)
