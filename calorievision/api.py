"""JSON API under /api/v1 for scripts and other front ends."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from .web import foods, history, record

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.errorhandler(404)
def not_found(_):
    return jsonify({"error": "not found"}), 404


@bp.get("/foods")
def list_foods():
    q = request.args.get("q", "").strip().lower()
    names = [n for n in foods().names() if q in n] if q else foods().names()
    return jsonify([{"name": n, **foods().foods[n]} for n in names])


@bp.get("/foods/<path:name>")
def get_food(name: str):
    item = foods().lookup(name)
    if not item.found:
        return jsonify({"error": "food not found", "did_you_mean": item.alternatives}), 404
    return jsonify(item.to_dict())


@bp.post("/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    text = data.get("text") or ""
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "send JSON like {\"text\": \"2 roti, dal\"}"}), 400
    items, total = foods().analyze(text)
    if data.get("save", True) and any(i.found for i in items):
        entry = record(items, total, source="api")
        return jsonify(entry), 201
    return jsonify({"items": [i.to_dict() for i in items], "total": total})


@bp.get("/history")
def list_history():
    return jsonify(history().all())


@bp.delete("/history/<entry_id>")
def delete_history(entry_id: str):
    if history().delete(entry_id):
        return "", 204
    return jsonify({"error": "not found"}), 404


@bp.get("/health")
def health():
    return jsonify({"ok": True, "foods": len(foods().foods), "vision": bool(current_app.config["ANTHROPIC_API_KEY"])})
