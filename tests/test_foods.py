from __future__ import annotations

import pytest

from calorievision.foods import ALIASES, parse_item, split_items


@pytest.mark.parametrize("text, expected", [
    ("roti", (1.0, "roti")),
    ("2 roti", (2.0, "roti")),
    ("roti x3", (3.0, "roti")),
    ("3x idli", (3.0, "idli")),
    ("half pizza", (0.5, "pizza")),
    ("1/2 cake", (0.5, "cake")),
    ("1.5 rice", (1.5, "rice")),
    ("two eggs", (2.0, "eggs")),
    ("a cup of tea", (1.0, "tea")),
    ("2 bowls of dal", (2.0, "dal")),
    ("  Palak   Paneer ", (1.0, "palak paneer")),
])
def test_parse_item(text, expected):
    assert parse_item(text) == expected


def test_split_items():
    assert split_items("2 roti, dal and rice + tea\ncoffee & milk") == [
        "2 roti", "dal", "rice", "tea", "coffee", "milk",
    ]
    assert split_items("") == []
    assert split_items(" , ,") == []


def test_aliases_point_at_real_foods(db):
    assert set(ALIASES.values()) <= set(db.foods)


def test_database_entries_are_well_formed(db):
    assert len(db.foods) >= 50
    for name, info in db.foods.items():
        assert name == name.lower().strip()
        assert isinstance(info["calories"], int) and info["calories"] > 0
        assert info["suggestion"]


@pytest.mark.parametrize("query, name, corrected", [
    ("rice", "rice", False),
    ("Apples", "apple", False),
    ("chapati", "roti", False),
    ("biryani", "biriyani", False),
    ("bananna", "banana", True),
    ("pizzza", "pizza", True),
])
def test_lookup_resolves(db, query, name, corrected):
    item = db.lookup(query)
    assert item.found
    assert item.name == name
    assert item.corrected is corrected


def test_lookup_scales_by_quantity(db):
    item = db.lookup("2 roti")
    assert item.total == 2 * db.foods["roti"]["calories"]
    assert db.lookup("half pizza").total == round(db.foods["pizza"]["calories"] / 2)


def test_unknown_food_offers_alternatives(db):
    item = db.lookup("paneer masala")
    assert not item.found
    assert item.total == 0
    assert "paneer butter masala" in item.alternatives
    assert not db.lookup("xyzzy").alternatives


def test_analyze_totals_only_found_items(db):
    items, total = db.analyze("2 roti, dal, xyzzy")
    assert [i.found for i in items] == [True, True, False]
    assert total == 2 * db.foods["roti"]["calories"] + db.foods["dal"]["calories"]


def test_from_detection_prefers_database(db):
    known = db.from_detection("Roti", 2, 999, "tip")
    assert (known.name, known.calories, known.estimated) == ("roti", db.foods["roti"]["calories"], False)
    unknown = db.from_detection("Gulab Jamun", 1, 150, "Sweet treat.")
    assert (unknown.name, unknown.calories, unknown.estimated) == ("gulab jamun", 150, True)
    assert unknown.suggestion == "Sweet treat."
