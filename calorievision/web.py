from __future__ import annotations

import datetime as dt
import uuid

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

bp = Blueprint("web", __name__)


def foods():
    return current_app.extensions["foods"]


def history():
    return current_app.extensions["history"]


def record(items, total, source="text") -> dict:
    entry = {
        "id": uuid.uuid4().hex,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": source,
        "items": [i.to_dict() for i in items],
        "total": total,
    }
    history().add(entry)
    return entry


@bp.route("/")
def index():
    return render_template("index.html", food_names=foods().names())


@bp.route("/get_calories")
def get_calories():
    item = foods().lookup(request.args.get("food", ""))
    if item.found:
        return jsonify({"food": item.name, "calories": item.calories, "suggestion": item.suggestion})
    return jsonify({"error": "Food not found in database", "did_you_mean": item.alternatives}), 404


@bp.route("/analyze", methods=["POST"])
def analyze():
    query = request.form.get("food", "")
    items, total = foods().analyze(query)
    if not any(i.found for i in items):
        hints = sorted({a for i in items for a in i.alternatives}) or foods().names()[:24]
        return render_template("notfound.html", query=query, suggestions=hints), 404
    entry = record(items, total)
    return render_template("result.html", results=entry["items"], total=total)


@bp.route("/history")
def history_page():
    return render_template("history.html", days=history().by_day())


@bp.route("/history/<entry_id>")
def history_entry(entry_id: str):
    entry = history().get(entry_id) or abort(404)
    return render_template("result.html", results=entry["items"], total=entry["total"], entry=entry)


@bp.post("/history/<entry_id>/delete")
def history_delete(entry_id: str):
    history().delete(entry_id)
    return redirect(url_for("web.history_page"))


@bp.post("/history/clear")
def history_clear():
    history().clear()
    return redirect(url_for("web.history_page"))
