from __future__ import annotations

import json
import threading
from pathlib import Path


class HistoryStore:
    """Append-only list of analyses in a JSON file, guarded by a lock."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def all(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def add(self, entry: dict) -> None:
        with self._lock:
            hist = self.all()
            hist.append(entry)
            self._write(hist)

    def _write(self, hist: list[dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(hist, indent=2), encoding="utf-8")
        tmp.replace(self.path)
