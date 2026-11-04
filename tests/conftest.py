from __future__ import annotations

import pytest

from calorievision import create_app
from calorievision.config import BASE_DIR
from calorievision.foods import FoodDB


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "HISTORY_PATH": tmp_path / "history.json",
        "ANTHROPIC_API_KEY": "",
    })
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def db():
    return FoodDB(BASE_DIR / "data" / "calories.json")
