from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict
from pathlib import Path

from loopora.diagnostics import get_logger, log_event
from loopora.settings_recent_workdirs import app_home

from dataclasses import dataclass

@dataclass(slots=True)
class AppSettings:
    max_concurrent_runs: int = 2
    polling_interval_seconds: float = 0.5
    stop_grace_period_seconds: float = 2.0
    role_idle_timeout_seconds: float = 300.0

logger = get_logger(__name__)


def persist_settings_best_effort(settings: AppSettings, *, path: Path) -> None:
    try:
        path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        log_event(
            logger,
            logging.WARNING,
            "settings.persist.write_failed",
            "Failed to persist settings; continuing with in-memory defaults",
            app_home=app_home(),
            path=path,
        )


def normalize_settings_payload(payload: object, *, defaults: AppSettings) -> tuple[AppSettings, bool]:
    if not isinstance(payload, dict):
        log_event(
            logger,
            logging.WARNING,
            "settings.normalize.invalid_payload",
            "Settings payload is not an object; resetting to defaults",
            payload_type=type(payload).__name__,
        )
        return defaults, True

    normalized: dict[str, float | int] = {}
    should_rewrite = False

    max_concurrent_runs = _coerce_setting_number(
        payload,
        key="max_concurrent_runs",
        default=defaults.max_concurrent_runs,
        integer_only=True,
        minimum=1,
    )
    if max_concurrent_runs != payload.get("max_concurrent_runs") or not _is_plain_int(payload.get("max_concurrent_runs")):
        should_rewrite = True
    normalized["max_concurrent_runs"] = int(max_concurrent_runs)

    polling_interval_seconds = _coerce_setting_number(
        payload,
        key="polling_interval_seconds",
        default=defaults.polling_interval_seconds,
        integer_only=False,
        minimum=0.001,
    )
    if polling_interval_seconds != payload.get("polling_interval_seconds"):
        should_rewrite = True
    normalized["polling_interval_seconds"] = polling_interval_seconds

    stop_grace_period_seconds = _coerce_setting_number(
        payload,
        key="stop_grace_period_seconds",
        default=defaults.stop_grace_period_seconds,
        integer_only=False,
        minimum=0.0,
    )
    if stop_grace_period_seconds != payload.get("stop_grace_period_seconds"):
        should_rewrite = True
    normalized["stop_grace_period_seconds"] = stop_grace_period_seconds

    role_idle_timeout_seconds = _coerce_setting_number(
        payload,
        key="role_idle_timeout_seconds",
        default=defaults.role_idle_timeout_seconds,
        integer_only=False,
        minimum=0.001,
    )
    if role_idle_timeout_seconds != payload.get("role_idle_timeout_seconds"):
        should_rewrite = True
    normalized["role_idle_timeout_seconds"] = role_idle_timeout_seconds

    expected_keys = set(normalized)
    if set(payload) != expected_keys:
        should_rewrite = True

    return AppSettings(**normalized), should_rewrite


def _coerce_setting_number(
    payload: dict[str, object],
    *,
    key: str,
    default: float,
    integer_only: bool,
    minimum: float,
) -> int | float:
    raw_value = payload.get(key, default)
    if isinstance(raw_value, bool):
        log_event(
            logger,
            logging.WARNING,
            "settings.normalize.invalid_value",
            "Invalid boolean-like settings value; using default",
            setting_key=key,
            raw_value=raw_value,
            default_value=default,
        )
        return default

    if integer_only and isinstance(raw_value, float) and not raw_value.is_integer():
        log_event(
            logger,
            logging.WARNING,
            "settings.normalize.invalid_value",
            "Invalid fractional integer settings value; using default",
            setting_key=key,
            raw_value=raw_value,
            default_value=default,
        )
        return default

    try:
        value = int(raw_value) if integer_only else float(raw_value)
    except (TypeError, ValueError, OverflowError):
        log_event(
            logger,
            logging.WARNING,
            "settings.normalize.invalid_value",
            "Invalid settings value; using default",
            setting_key=key,
            raw_value=raw_value,
            default_value=default,
        )
        return default

    if value < minimum:
        log_event(
            logger,
            logging.WARNING,
            "settings.normalize.out_of_range",
            "Out-of-range settings value; using default",
            setting_key=key,
            raw_value=raw_value,
            default_value=default,
            minimum=minimum,
        )
        return default
    if isinstance(value, float) and not math.isfinite(value):
        log_event(
            logger,
            logging.WARNING,
            "settings.normalize.out_of_range",
            "Non-finite settings value; using default",
            setting_key=key,
            raw_value=raw_value,
            default_value=default,
        )
        return default
    return value


def _is_plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
