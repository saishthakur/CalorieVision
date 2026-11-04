from __future__ import annotations

from flask import Flask

from .config import BASE_DIR, Config


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    from .foods import FoodDB
    from .history import HistoryStore

    app.config["DATA_DIR"].mkdir(parents=True, exist_ok=True)
    app.extensions["foods"] = FoodDB(app.config["FOODS_PATH"])
    app.extensions["history"] = HistoryStore(app.config["HISTORY_PATH"])

    from .api import bp as api_bp
    from .web import bp as web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    return app
