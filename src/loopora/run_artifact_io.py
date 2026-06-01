from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from pathlib import Path

from loopora.diagnostics import get_logger, log_exception
from loopora.utils import append_jsonl, ensure_parent, read_json, write_json

logger = get_logger(__name__)

INITIAL_STAGNATION_STATE = {
    "stagnation_mode": "none",
    "recent_composites": [],
    "recent_deltas": [],
    "consecutive_low_delta": 0,
}


def read_stagnation_state(path: Path) -> dict:
    try:
        payload = read_json(path)
    except (OSError, UnicodeError, ValueError) as exc:
        log_exception(
            logger,
            "run_artifact.stagnation_read_failed",
            "Failed to read run stagnation state; resetting to initial state",
            error=exc,
            level=logging.WARNING,
            path=path,
        )
        return dict(INITIAL_STAGNATION_STATE)
    return payload if isinstance(payload, dict) and payload else dict(INITIAL_STAGNATION_STATE)


def append_jsonl_with_mirrors(path: Path, payload: dict, *, mirror_paths: Iterable[Path] = ()) -> None:
    append_jsonl(path, payload)
    for mirror_path in mirror_paths:
        if mirror_path == path:
            continue
        try:
            append_jsonl(mirror_path, payload)
        except Exception as exc:  # noqa: BLE001 - legacy mirrors are best-effort once canonical write succeeds.
            _log_mirror_write_failure(exc, operation="append_jsonl", canonical_path=path, mirror_path=mirror_path)


def write_json_with_mirrors(path: Path, payload: dict, *, mirror_paths: Iterable[Path] = ()) -> None:
    write_json(path, payload)
    for mirror_path in mirror_paths:
        if mirror_path == path:
            continue
        try:
            write_json(mirror_path, payload)
        except Exception as exc:  # noqa: BLE001 - legacy mirrors are best-effort once canonical write succeeds.
            _log_mirror_write_failure(exc, operation="write_json", canonical_path=path, mirror_path=mirror_path)


def write_text_with_mirrors(path: Path, text: str, *, mirror_paths: Iterable[Path] = ()) -> None:
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")
    for mirror_path in mirror_paths:
        if mirror_path == path:
            continue
        try:
            ensure_parent(mirror_path)
            mirror_path.write_text(text, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 - legacy mirrors are best-effort once canonical write succeeds.
            _log_mirror_write_failure(exc, operation="write_text", canonical_path=path, mirror_path=mirror_path)


def _log_mirror_write_failure(exc: Exception, *, operation: str, canonical_path: Path, mirror_path: Path) -> None:
    log_exception(
        logger,
        "run_artifact.mirror_write_failed",
        "Failed to write legacy run artifact mirror",
        error=exc,
        level=logging.WARNING,
        operation=operation,
        canonical_path=canonical_path,
        mirror_path=mirror_path,
    )


def read_jsonl(path: Path, *, limit: int | None = None) -> list[dict]:
    if not path.exists() or not path.is_file():
        return []
    records: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        log_exception(
            logger,
            "run_artifact.jsonl_read_failed",
            "Failed to read run artifact JSONL; returning no records",
            error=exc,
            level=logging.WARNING,
            path=path,
        )
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    if limit is not None and limit >= 0:
        return records[-limit:]
    return records
