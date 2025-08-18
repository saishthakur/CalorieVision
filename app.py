# =============================
# FILE: app.py
# =============================
from __future__ import annotations
from flask import Flask, request, jsonify, render_template, redirect, url_for
from pathlib import Path
import json
import datetime as dt
import uuid

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
CAL_PATH = DATA / "calories.json"
HISTORY_PATH = DATA / "history.json"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.update(TEMPLATES_AUTO_RELOAD=True)

# --- seed JSON if missing ---
if not CAL_PATH.exists():
    seed = {
        "apple": {"calories": 95, "suggestion": "Great snack; high fiber."},
        "banana": {"calories": 105, "suggestion": "Add peanut butter for protein."},
        "rice": {"calories": 200, "suggestion": "Pair with veggies to balance."},
        "roti": {"calories": 120, "suggestion": "Pair with dal for protein."},
        "dosa": {"calories": 168, "suggestion": "Go easy on oil; add sambar."}
    }
    CAL_PATH.write_text(json.dumps(seed, indent=2))
if not HISTORY_PATH.exists():
    HISTORY_PATH.write_text(json.dumps([], indent=2))


def load_db() -> dict:
    return json.loads(CAL_PATH.read_text(encoding="utf-8"))


def save_history(entry: dict) -> None:
    try:
        hist = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        hist = []
    hist.append(entry)
    HISTORY_PATH.write_text(json.dumps(hist, indent=2), encoding="utf-8")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_calories", methods=["GET"])  # JSON API
def get_calories():
    db = load_db()
    food = request.args.get("food", "").strip().lower()
    if food in db:
        return jsonify({
            "food": food,
            "calories": db[food]["calories"],
            "suggestion": db[food]["suggestion"]
        })
    return jsonify({"error": "Food not found in database"}), 404


@app.route("/analyze", methods=["POST"])  # form submit
def analyze():
    db = load_db()
    foods_input = request.form.get("food", "").lower()
    foods = [f.strip() for f in foods_input.split(",") if f.strip()]
    results, total = [], 0
    for name in foods:
        if name in db:
            cal = db[name]["calories"]
            total += cal
            results.append({"name": name, "calories": cal, "suggestion": db[name]["suggestion"]})
        else:
            results.append({"name": name, "calories": None, "suggestion": None})
    entry = {
        "id": uuid.uuid4().hex,
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "items": results,
        "total": total,
    }
    save_history(entry)
    # If any not-found items exist, send to notfound with hints
    missing = [r for r in results if r["calories"] is None]
    if missing and len(results) == 1:
        return render_template("notfound.html", query=foods_input, suggestions=list(db.keys())[:24])
    return render_template("result.html", results=results, total=total)


# -------------- main --------------
if __name__ == "__main__":
    app.run(debug=True)