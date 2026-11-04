# 🍽️ Calorie Vision

Calorie Vision is a Flask web app that estimates the calories in a meal. You can type what you ate, or upload a photo and let Claude recognize the foods.

![tests](https://github.com/saishthakur/CalorieVision/actions/workflows/tests.yml/badge.svg)

## Features

- **Type your meal in plain words.** Input like `2 roti, dal and rice`, `half pizza`, `idli x3` or `a bowl of dal` works. Quantities scale the calories.
- **Forgiving matching.** Typos are auto-corrected (`pizzza` → pizza). Plurals (`apples`) and common alternate names (`chapati` → roti, `biryani`) are understood. Unknown items get "did you mean" suggestions.
- **📷 Photo recognition.** Upload a meal photo. Claude lists each food with a serving count. Foods in the local database use its calorie values; anything else gets an AI estimate and is clearly tagged as one.
- **History and a daily goal.** Every analysis is saved and grouped by day. Progress is shown against a daily calorie goal you can edit. You can reopen, delete or clear entries.
- **JSON API** for scripts and other front ends (see below).
- **58 foods**, including many Indian dishes. Each entry has a calorie value per standard serving and a short tip.

## Quick start

```bash
git clone https://github.com/saishthakur/CalorieVision.git
cd CalorieVision
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # optional: add ANTHROPIC_API_KEY for photo recognition
python app.py
```

Then open http://localhost:5000.

Without an API key everything works except photo upload, which shows as disabled.

## Configuration

Set these in `.env` or as environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | *(empty)* | Turns on photo recognition. |
| `CALORIEVISION_VISION_MODEL` | `claude-opus-5-5` | Claude model used for photos. |
| `CALORIEVISION_DATA_DIR` | `./data` | Where `calories.json` and `history.json` live. |
| `FLASK_DEBUG` | off | Set to `1` for auto-reload and debug pages. |
| `SECRET_KEY` | dev value | Set a real value in production. |

## JSON API

All endpoints live under `/api/v1`.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/foods?q=egg` | List foods, optionally filtered by a search term. |
| `GET` | `/foods/<text>` | Look up one item, e.g. `/foods/2 roti`. Returns 404 with `did_you_mean` on a miss. |
| `POST` | `/analyze` | Analyze a meal from `{"text": "2 roti, dal", "save": true}`. |
| `POST` | `/analyze-photo` | Analyze a meal from a multipart upload with a `photo` field. |
| `GET` | `/history` | List all saved analyses. |
| `DELETE` | `/history/<id>` | Delete one saved analysis. |
| `GET` | `/health` | Report status, food count and whether photo recognition is on. |

```bash
curl -X POST localhost:5000/api/v1/analyze -H "Content-Type: application/json" \
     -d '{"text": "2 roti, dal and rice"}'
```

## Project layout

```
app.py                  entry point (loads .env, creates the app)
calorievision/
  __init__.py           app factory
  config.py             settings from the environment
  foods.py              food DB, quantity parsing, fuzzy matching
  history.py            JSON-file history with locking and atomic writes
  vision.py             Claude photo recognition
  web.py                HTML routes
  api.py                JSON API
data/calories.json      the food database
templates/, static/     UI (Bootstrap 5 + a shared stylesheet)
tests/                  pytest suite
```

## Adding foods

Add an entry to `data/calories.json`. The key is the lowercase name, and `calories` is per standard serving:

```json
"masala dosa": { "calories": 250, "suggestion": "Pair with sambar for protein." }
```

For alternate names, add a mapping to `ALIASES` in `calorievision/foods.py`.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests mock the Claude call, so they don't need an API key and don't use the network.

## Roadmap

- Macronutrients (protein, carbs and fat) per food
- Per-user accounts in place of a single shared history file
- Portion-size hints from the photo, such as plate size and grams

---

Calorie values are approximate and meant for general awareness. This app is not medical or dietary advice.
