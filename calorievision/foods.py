from __future__ import annotations

import difflib
import json
import re
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path

# Common alternate spellings/names mapped to the canonical DB key.
ALIASES = {
    "chapati": "roti",
    "chapathi": "roti",
    "phulka": "roti",
    "biryani": "biriyani",
    "chole bhature": "chole",
    "chickpeas": "chana",
    "kidney beans": "rajma",
    "eggs": "egg",
    "fries": "french fries",
    "chips": "french fries",
    "cold drink": "soda",
    "coke": "soda",
    "juice": "fruit juice",
    "chaas": "buttermilk",
    "omelet": "omelette",
}

WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "half": 0.5, "quarter": 0.25, "double": 2,
}

_NUM = r"(\d+(?:\.\d+)?|\d+/\d+)"
_LEADING = re.compile(rf"^{_NUM}\s*(?:x|×)?\s+(.+)$")
_TRAILING = re.compile(rf"^(.+?)\s*(?:x|×)\s*{_NUM}$")

# Serving words dropped from the front of a name: "2 bowls of dal" -> "dal".
UNITS = re.compile(
    r"^(?:cups?|bowls?|plates?|glass(?:es)?|slices?|pieces?|pcs|servings?|"
    r"portions?|katoris?|mugs?|scoops?)\s+(?:of\s+)?"
)

AUTO_CORRECT_CUTOFF = 0.82
SUGGEST_CUTOFF = 0.55


def _to_number(token: str) -> float:
    return float(Fraction(token))


def parse_item(text: str) -> tuple[float, str]:
    """Split "2 roti", "roti x2", "half pizza", "a bowl of dal" into (qty, name)."""
    qty, name = _parse_qty(text)
    return qty, UNITS.sub("", name).strip() or name


def _parse_qty(text: str) -> tuple[float, str]:
    text = " ".join(text.strip().lower().split())
    if m := _LEADING.match(text):
        return _to_number(m.group(1)), m.group(2).strip()
    if m := _TRAILING.match(text):
        return _to_number(m.group(2)), m.group(1).strip()
    first, _, rest = text.partition(" ")
    if rest and first in WORD_NUMBERS:
        rest = rest.removeprefix("of ").strip()
        return float(WORD_NUMBERS[first]), rest
    return 1.0, text


def split_items(text: str) -> list[str]:
    """Split user input on commas, "and", "+", and newlines."""
    parts = re.split(r",|\n|\+|\band\b|&", text or "")
    return [p.strip() for p in parts if p.strip()]


@dataclass
class Item:
    query: str
    qty: float = 1.0
    name: str | None = None
    calories: int | None = None  # per serving
    suggestion: str | None = None
    corrected: bool = False
    alternatives: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.name is not None

    @property
    def total(self) -> int:
        return round((self.calories or 0) * self.qty)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["found"] = self.found
        d["total"] = self.total if self.found else None
        return d


class FoodDB:
    """Calorie lookup backed by a JSON file of {name: {calories, suggestion}}."""

    def __init__(self, path: Path):
        self.path = path
        self.foods: dict[str, dict] = json.loads(path.read_text(encoding="utf-8"))

    def names(self) -> list[str]:
        return sorted(self.foods)

    def get(self, name: str) -> dict | None:
        return self.foods.get(name.strip().lower())

    def resolve(self, name: str) -> tuple[str | None, bool, list[str]]:
        """Return (canonical name, was_corrected, alternatives)."""
        name = " ".join(name.strip().lower().split())
        if name in self.foods:
            return name, False, []
        if name in ALIASES:
            return ALIASES[name], False, []
        for stem in (name.removesuffix("es"), name.removesuffix("s")):
            if stem != name and stem in self.foods:
                return stem, False, []
        candidates = list(self.foods) + list(ALIASES)
        close = difflib.get_close_matches(name, candidates, n=4, cutoff=SUGGEST_CUTOFF)
        close = list(dict.fromkeys(ALIASES.get(c, c) for c in close))
        if close and difflib.SequenceMatcher(None, name, close[0]).ratio() >= AUTO_CORRECT_CUTOFF:
            return close[0], True, close[1:]
        return None, False, close

    def lookup(self, text: str) -> Item:
        qty, raw = parse_item(text)
        item = Item(query=text.strip(), qty=qty)
        name, corrected, alts = self.resolve(raw)
        item.alternatives = alts
        if name:
            info = self.foods[name]
            item.name, item.corrected = name, corrected
            item.calories, item.suggestion = info["calories"], info["suggestion"]
        return item

    def analyze(self, text: str) -> tuple[list[Item], int]:
        items = [self.lookup(part) for part in split_items(text)]
        return items, sum(i.total for i in items if i.found)
