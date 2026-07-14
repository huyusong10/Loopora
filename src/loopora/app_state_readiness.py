from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import sqlite3

from loopora.branding import app_home_path
from loopora.db_schema_v3 import CURRENT_SCHEMA_VERSION, schema_has_current_v3_shape


def app_state_report(_root: Path, *, commands: Mapping[str, str] | None = None) -> dict:
    home = app_home_path()
    database = home / "app.db"
    base: dict[str, object] = {
        "app_home": str(home),
        "db_path": str(database),
        "schema_version": None,
        "current_schema_version": CURRENT_SCHEMA_VERSION,
        "web_ready": True,
        "needs_attention": False,
        "next_action": "start_web_when_needed",
        "commands": dict(commands or {}),
    }
    if not database.exists():
        return {
            **base,
            "status": "not_initialized",
            "summary": "App database has not been created yet; Web will initialize it on first start.",
        }

    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            db_version = _schema_user_version(connection)
            has_current_shape = schema_has_current_v3_shape(connection)
    except sqlite3.Error:
        return {
            **base,
            "status": "unreadable",
            "summary": "App database could not be read; inspect or reset local App state.",
            "web_ready": False,
            "needs_attention": True,
            "next_action": "inspect_or_reset_app_state",
        }

    report = {
        **base,
        "schema_version": db_version,
        "has_current_shape": has_current_shape,
        "status": "current",
        "summary": "App database schema is current.",
    }
    if db_version > CURRENT_SCHEMA_VERSION:
        return {
            **report,
            "status": "future_version",
            "summary": (
                "App database was created by a newer Loopora version; use a matching or newer Loopora version, "
                "or create a private recovery archive before previewing an app-scope reset."
            ),
            "web_ready": False,
            "needs_attention": True,
            "next_action": "use_matching_loopora_version_or_reset",
        }
    if db_version == CURRENT_SCHEMA_VERSION and has_current_shape:
        return report
    if db_version == 0 and has_current_shape:
        return {
            **report,
            "status": "current_shape_unversioned",
            "summary": "App database has the current shape but no version stamp; Web will stamp it on start.",
            "next_action": "start_web_when_needed",
        }
    return {
        **report,
        "status": "development_reset_required",
        "summary": "Existing local App database is incompatible; create a private recovery archive before previewing the App database reset scope.",
        "web_ready": False,
        "needs_attention": True,
        "next_action": "preview_dev_reset_before_web",
    }


def app_state_web_readiness_blockers(app_state: Mapping[str, object]) -> list[dict[str, str]]:
    if app_state.get("web_ready") is not False:
        return []
    return [
        {
            "kind": "app_state_not_ready",
            "status": str(app_state.get("status") or "unknown").strip() or "unknown",
            "recovery_action": app_state_web_recovery_action(app_state),
        }
    ]


def app_state_web_recovery_action(app_state: Mapping[str, object]) -> str:
    next_action = str(app_state.get("next_action") or "").strip()
    if next_action == "preview_dev_reset_before_web":
        return "preview_app_database_reset"
    if next_action in {"inspect_or_reset_app_state", "use_matching_loopora_version_or_reset"}:
        return next_action
    return "inspect_app_state" if app_state.get("web_ready") is False else ""


def _schema_user_version(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0] or 0)
