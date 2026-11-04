from __future__ import annotations

import json
from pathlib import Path


class FoodDB:
    """Calorie lookup backed by a JSON file of {name: {calories, suggestion}}."""

    def __init__(self, path: Path):
        self.path = path
        self.foods: dict[str, dict] = json.loads(path.read_text(encoding="utf-8"))

    def names(self) -> list[str]:
        return sorted(self.foods)

    def get(self, name: str) -> dict | None:
        return self.foods.get(name.strip().lower())
