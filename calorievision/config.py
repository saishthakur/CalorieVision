from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-not-secret")
    DATA_DIR = Path(os.environ.get("CALORIEVISION_DATA_DIR", BASE_DIR / "data"))
    FOODS_PATH = DATA_DIR / "calories.json"
    HISTORY_PATH = DATA_DIR / "history.json"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB uploads
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    VISION_MODEL = os.environ.get("CALORIEVISION_VISION_MODEL", "claude-opus-5-5")
    TEMPLATES_AUTO_RELOAD = True
