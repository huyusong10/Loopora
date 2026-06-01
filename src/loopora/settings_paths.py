from __future__ import annotations

from pathlib import Path

from loopora.branding import app_home_path


def app_home() -> Path:
    path = app_home_path()
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = app_home() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return app_home() / "settings.json"


def db_path() -> Path:
    return app_home() / "app.db"


def recent_workdirs_path() -> Path:
    return app_home() / "recent_workdirs.json"
