from __future__ import annotations

import io
import json
from unittest import mock

from calorievision.vision import DetectedFood

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert b"What did you eat?" in r.data
    assert b"Photo recognition is off" in r.data


def test_analyze_renders_and_records(client, app):
    r = client.post("/analyze", data={"food": "2 roti, pizzza, xyzzy"})
    assert r.status_code == 200
    assert b"2 \xc3\x97 roti" in r.data  # "2 × roti"
    assert "from “pizzza”".encode() in r.data
    assert b"Not in our database" in r.data
    hist = app.extensions["history"].all()
    assert len(hist) == 1 and hist[0]["total"] == 240 + 270


def test_analyze_nothing_found(client, app):
    r = client.post("/analyze", data={"food": "xyzzy"})
    assert r.status_code == 404
    assert b"couldn't find that" in r.data
    assert app.extensions["history"].all() == []


def test_notfound_page_escapes_query(client):
    r = client.post("/analyze", data={"food": "<script>alert(1)</script>"})
    assert b"<script>alert(1)" not in r.data


def test_get_calories(client):
    assert client.get("/get_calories?food=Mango").json["calories"] == 150
    r = client.get("/get_calories?food=mangoo")
    assert r.json["food"] == "mango"
    assert client.get("/get_calories?food=xyzzy").status_code == 404


def test_history_pages(client, app):
    client.post("/analyze", data={"food": "rice"})
    entry_id = app.extensions["history"].all()[0]["id"]
    assert b"Rice" in client.get("/history").data or b"rice" in client.get("/history").data
    assert client.get(f"/history/{entry_id}").status_code == 200
    assert client.get("/history/nope").status_code == 404
    assert client.post(f"/history/{entry_id}/delete").status_code == 302
    assert app.extensions["history"].all() == []


def test_history_clear(client, app):
    client.post("/analyze", data={"food": "rice"})
    client.post("/analyze", data={"food": "dal"})
    client.post("/history/clear")
    assert app.extensions["history"].all() == []


def test_legacy_history_entries_are_upgraded(app, client):
    legacy = [{
        "id": "old1", "timestamp": "2025-10-01T08:00:00Z", "total": 200,
        "items": [{"name": "rice", "calories": 200, "suggestion": "x"},
                  {"name": "zzz", "calories": None, "suggestion": None}],
    }]
    app.config["HISTORY_PATH"].write_text(json.dumps(legacy))
    entry = app.extensions["history"].get("old1")
    assert [i["found"] for i in entry["items"]] == [True, False]
    assert client.get("/history").status_code == 200
    assert client.get("/history/old1").status_code == 200


def test_photo_disabled_without_key(client):
    r = client.post("/analyze-photo", data={"photo": (io.BytesIO(PNG), "a.png")})
    assert r.status_code == 400
    assert b"ANTHROPIC_API_KEY" in r.data


def test_photo_rejects_non_images(client, app):
    app.config["ANTHROPIC_API_KEY"] = "test"
    r = client.post("/analyze-photo", data={"photo": (io.BytesIO(b"hello"), "a.txt")})
    assert r.status_code == 400
    assert b"JPEG, PNG" in r.data


def test_photo_success(client, app):
    app.config["ANTHROPIC_API_KEY"] = "test"
    fake = [DetectedFood(name="dosa", quantity=1, calories_per_serving=200, tip="t"),
            DetectedFood(name="coconut chutney", quantity=1, calories_per_serving=90, tip="Go easy.")]
    with mock.patch("calorievision.web.identify_foods", return_value=fake) as identify:
        r = client.post("/analyze-photo", data={"photo": (io.BytesIO(PNG), "meal.png")})
    assert r.status_code == 200
    assert b"AI estimate" in r.data
    assert identify.call_args.kwargs["model"] == app.config["VISION_MODEL"]
    entry = app.extensions["history"].all()[0]
    assert entry["source"] == "photo"
    assert entry["total"] == 160 + 90  # dosa from DB, chutney estimated
