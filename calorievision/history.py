from __future__ import annotations

import datetime as dt
import json
from collections import OrderedDict
import threading
from pathlib import Path


def _upgrade(entry: dict) -> dict:
    """Fill in fields missing from entries saved by the original app.py."""
    entry.setdefault("source", "text")
    for item in entry.get("items", []):
        found = item.setdefault("found", item.get("calories") is not None)
        item.setdefault("query", item.get("name"))
        item.setdefault("qty", 1)
        item.setdefault("total", item.get("calories") if found else None)
        item.setdefault("corrected", False)
        item.setdefault("estimated", False)
        item.setdefault("alternatives", [])
    return entry


class HistoryStore:
    """Append-only list of analyses in a JSON file, guarded by a lock."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def all(self) -> list[dict]:
        try:
            hist = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        return [_upgrade(e) for e in hist]

    def add(self, entry: dict) -> None:
        with self._lock:
            hist = self.all()
            hist.append(entry)
            self._write(hist)

    def get(self, entry_id: str) -> dict | None:
        return next((e for e in self.all() if e.get("id") == entry_id), None)

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            hist = self.all()
            kept = [e for e in hist if e.get("id") != entry_id]
            if len(kept) == len(hist):
                return False
            self._write(kept)
            return True

    def clear(self) -> None:
        with self._lock:
            self._write([])

    def by_day(self, tz: dt.tzinfo | None = None) -> "OrderedDict[str, dict]":
        """Group entries by local calendar day, newest first, with day totals."""
        days: OrderedDict[str, dict] = OrderedDict()
        for entry in sorted(self.all(), key=lambda e: e.get("timestamp", ""), reverse=True):
            try:
                when = dt.datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            day = when.astimezone(tz).date().isoformat()
            bucket = days.setdefault(day, {"total": 0, "entries": []})
            bucket["total"] += entry.get("total", 0)
            bucket["entries"].append({**entry, "local_time": when.astimezone(tz).strftime("%H:%M")})
        return days

    def _write(self, hist: list[dict]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(hist, indent=2), encoding="utf-8")
        tmp.replace(self.path)
