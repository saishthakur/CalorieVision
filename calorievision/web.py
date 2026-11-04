from __future__ import annotations

import datetime as dt
import uuid

from flask import Blueprint, current_app, jsonify, render_template, request

bp = Blueprint("web", __name__)


def foods():
    return current_app.extensions["foods"]


def history():
    return current_app.extensions["history"]


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/get_calories")
def get_calories():
    food = request.args.get("food", "").strip().lower()
    info = foods().get(food)
    if info:
        return jsonify({"food": food, **info})
    return jsonify({"error": "Food not found in database"}), 404


@bp.route("/analyze", methods=["POST"])
def analyze():
    foods_input = request.form.get("food", "").lower()
    names = [f.strip() for f in foods_input.split(",") if f.strip()]
    results, total = [], 0
    for name in names:
        info = foods().get(name)
        if info:
            total += info["calories"]
            results.append({"name": name, **info})
        else:
            results.append({"name": name, "calories": None, "suggestion": None})
    history().add({
        "id": uuid.uuid4().hex,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "items": results,
        "total": total,
    })
    missing = [r for r in results if r["calories"] is None]
    if missing and len(results) == 1:
        return render_template("notfound.html", query=foods_input, suggestions=foods().names()[:24])
    return render_template("result.html", results=results, total=total)
