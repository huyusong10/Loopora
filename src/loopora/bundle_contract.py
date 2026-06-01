from __future__ import annotations

from loopora.strategy_source import StrategySourceError, normalize_strategy_source_identifier

BUNDLE_VERSION = 1
BUNDLE_DEFAULT_LOOP = {
    "completion_mode": "gatekeeper",
    "executor_kind": "codex",
    "executor_mode": "preset",
    "command_cli": "",
    "command_args_text": "",
    "model": "",
    "reasoning_effort": "",
    "iteration_interval_seconds": 0.0,
    "max_iters": 8,
    "max_role_retries": 2,
    "delta_threshold": 0.005,
    "trigger_window": 4,
    "regression_window": 2,
}
BUNDLE_EXECUTION_FIELDS = (
    "executor_kind",
    "executor_mode",
    "command_cli",
    "command_args_text",
    "model",
    "reasoning_effort",
)


class BundleError(ValueError):
    """Raised when a YAML bundle cannot be parsed or normalized."""


def normalize_bundle_identifier(value: object, *, field_name: str = "bundle id", allow_empty: bool = False) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        if allow_empty:
            return ""
        raise BundleError(f"{field_name} is required")
    try:
        return normalize_strategy_source_identifier(value, field_name=field_name)
    except StrategySourceError as exc:
        raise BundleError(str(exc)) from exc


def normalize_bundle_integer(value: object, *, default: int, field_name: str) -> int:
    if value is None:
        return default
    if isinstance(value, str) and not value.strip():
        return default
    if isinstance(value, bool):
        raise BundleError(f"{field_name} must be an integer")
    if isinstance(value, float):
        raise BundleError(f"{field_name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise BundleError(f"{field_name} must be an integer") from exc
