from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from pathlib import Path

from loopora.diagnostics import get_logger, log_event
from loopora.settings_payloads import write_settings_text_atomically
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
            logging.INFO,
            "settings.recent_workdirs.read_failed",
            "Failed to read recent workdirs; ignoring stored entries",
            app_home=app_home(),
            path=path,
        )
        return []
    if not isinstance(payload, list):
        return []
    return _normalize_recent_workdirs(payload, limit=limit, stored=True)


def save_recent_workdirs(workdirs: Iterable[str], limit: int = 50) -> None:
    recent = _normalize_recent_workdirs(workdirs, limit=limit, stored=False)
    path = recent_workdirs_path()
    try:
        write_settings_text_atomically(
            path,
            json.dumps(recent, ensure_ascii=False, indent=2) + "\n",
        )
    except OSError:
        log_event(
            logger,
            logging.INFO,
            "settings.recent_workdirs.write_failed",
            "Failed to write recent workdirs; update ignored",
            app_home=app_home(),
            path=path,
        )


def remember_recent_workdir(workdir: object, limit: int = 50) -> None:
    value = _normalize_recent_workdir_entry(workdir, stored=False)
    if not value:
        return
    save_recent_workdirs([value, *load_recent_workdirs(limit=limit)], limit=limit)


def _normalize_recent_workdirs(workdirs: Iterable[object], *, limit: int, stored: bool) -> list[str]:
    recent = []
    seen = set()
    for item in workdirs:
        value = _normalize_recent_workdir_entry(item, stored=stored)
        if not value or value in seen:
            continue
        recent.append(value)
        seen.add(value)
        if len(recent) >= limit:
            break
    return recent


def _normalize_recent_workdir_entry(item: object, *, stored: bool) -> str:
    if isinstance(item, str):
        value = item.strip()
    elif isinstance(item, os.PathLike):
        value = os.fspath(item).strip()
    else:
        return ""
    if not value:
        return ""
    path = Path(value).expanduser()
    if stored and not path.is_absolute():
        return ""
    if path.is_absolute():
        return str(path.absolute())
    return str((Path.cwd() / path).absolute())
