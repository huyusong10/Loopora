from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable

from loopora.diagnostics import get_logger, log_event
from loopora.settings_paths import app_home, recent_workdirs_path

logger = get_logger(__name__)


def load_recent_workdirs(limit: int = 50) -> list[str]:
    path = recent_workdirs_path()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        log_event(
            logger,
            logging.WARNING,
            "settings.recent_workdirs.read_failed",
            "Failed to read recent workdirs; ignoring stored entries",
            app_home=app_home(),
            path=path,
        )
        return []
    if not isinstance(payload, list):
        return []
    return _normalize_recent_workdirs(payload, limit=limit)


def save_recent_workdirs(workdirs: Iterable[str], limit: int = 50) -> None:
    recent = _normalize_recent_workdirs(workdirs, limit=limit)
    path = recent_workdirs_path()
    try:
        path.write_text(
            json.dumps(recent, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        log_event(
            logger,
            logging.WARNING,
            "settings.recent_workdirs.write_failed",
            "Failed to write recent workdirs; update ignored",
            app_home=app_home(),
            path=path,
        )


def _normalize_recent_workdirs(workdirs: Iterable[object], *, limit: int) -> list[str]:
    recent = []
    seen = set()
    for item in workdirs:
        value = _normalize_recent_workdir_entry(item)
        if not value or value in seen:
            continue
        recent.append(value)
        seen.add(value)
        if len(recent) >= limit:
            break
    return recent


def _normalize_recent_workdir_entry(item: object) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, os.PathLike):
        return os.fspath(item).strip()
    return ""
