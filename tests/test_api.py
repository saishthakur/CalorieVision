from __future__ import annotations

import io
from unittest import mock

import anthropic
import httpx2

from calorievision.vision import DetectedFood, VisionError, identify_foods, sniff_media_type

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16


def test_health(client):
    assert client.get("/api/v1/health").json == {"ok": True, "foods": 58, "vision": False}


def test_list_and_search_foods(client):
    assert len(client.get("/api/v1/foods").json) == 58
    names = [f["name"] for f in client.get("/api/v1/foods?q=egg").json]
    assert names == ["boiled egg", "egg", "scrambled eggs"]


def test_get_food(client):
    assert client.get("/api/v1/foods/2 roti").json["total"] == 240
    miss = client.get("/api/v1/foods/paneer masala")
    assert miss.status_code == 404
    assert "paneer butter masala" in miss.json["did_you_mean"]


def test_analyze_saves_by_default(client):
    r = client.post("/api/v1/analyze", json={"text": "2 roti, dal"})
    assert r.status_code == 201
    assert r.json["total"] == 360
    assert client.get("/api/v1/history").json[0]["id"] == r.json["id"]


def test_analyze_without_saving(client):
    r = client.post("/api/v1/analyze", json={"text": "rice", "save": False})
    assert r.status_code == 200 and r.json["total"] == 200
    assert client.get("/api/v1/history").json == []


def test_analyze_validates_input(client):
    assert client.post("/api/v1/analyze", json={}).status_code == 400
    assert client.post("/api/v1/analyze", json={"text": 5}).status_code == 400
    assert client.post("/api/v1/analyze", data="nope").status_code == 400


def test_delete_history(client):
    entry_id = client.post("/api/v1/analyze", json={"text": "rice"}).json["id"]
    assert client.delete(f"/api/v1/history/{entry_id}").status_code == 204
    assert client.delete(f"/api/v1/history/{entry_id}").status_code == 404


def test_photo_endpoint(client, app):
    app.config["ANTHROPIC_API_KEY"] = "test"
    fake = [DetectedFood(name="banana", quantity=2, calories_per_serving=100, tip="t")]
    with mock.patch("calorievision.web.identify_foods", return_value=fake):
        r = client.post("/api/v1/analyze-photo", data={"photo": (io.BytesIO(PNG), "a.png")})
    assert r.status_code == 201
    assert r.json["total"] == 210 and r.json["source"] == "api-photo"
    assert client.post("/api/v1/analyze-photo").status_code == 400


def test_sniff_media_type():
    assert sniff_media_type(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert sniff_media_type(PNG) == "image/png"
    assert sniff_media_type(b"GIF89a...") == "image/gif"
    assert sniff_media_type(b"RIFF\0\0\0\0WEBPVP8 ") == "image/webp"
    assert sniff_media_type(b"%PDF-1.7") is None


def _status_error(cls, code):
    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("boom", response=httpx2.Response(code, request=request), body=None)


def test_identify_foods_maps_api_errors():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="PNG")
    png = buf.getvalue()
    for exc, needle in [
        (_status_error(anthropic.AuthenticationError, 401), "key was rejected"),
        (_status_error(anthropic.RateLimitError, 429), "Too many"),
        (_status_error(anthropic.InternalServerError, 500), "(500)"),
    ]:
        with mock.patch("anthropic.resources.beta.messages.Messages.parse", side_effect=exc):
            try:
                identify_foods(png, api_key="k", model="m", known_foods=["rice"])
            except VisionError as e:
                assert needle in str(e)
            else:
                raise AssertionError("expected VisionError")
