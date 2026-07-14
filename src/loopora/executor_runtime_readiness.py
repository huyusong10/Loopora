from __future__ import annotations

import shutil
import logging
from collections.abc import Callable, Mapping
from pathlib import Path

from loopora.executor_real import RealCodexExecutor
from loopora.executor_types import CodexExecutor
from loopora.diagnostics import get_logger, log_exception
from loopora.providers import executor_profile, list_executor_profiles, normalize_executor_kind, normalize_executor_mode
from loopora.service_alignment_executor_settings import (
    alignment_executor_settings_from_raw,
    normalize_alignment_executor_settings,
)
from loopora.service_types import LooporaError

logger = get_logger(__name__)


def executor_runtime_readiness(
    executor_factory: Callable[[], CodexExecutor],
    raw_settings: Mapping[str, object],
) -> dict[str, object]:
    request = alignment_executor_settings_from_raw(dict(raw_settings))
    try:
        executor_kind = normalize_executor_kind(request.executor_kind)
        executor_mode = normalize_executor_mode(request.executor_mode)
    except ValueError as exc:
        raise LooporaError(str(exc)) from exc

    profile = executor_profile(executor_kind)
    if profile.command_only:
        executor_mode = "command"
    command = request.command_cli if executor_mode == "command" else profile.cli_name
    projection = {
        "schema_version": 1,
        "executor_kind": executor_kind,
        "executor_mode": executor_mode,
        "executor_label": profile.label,
        "command_name": Path(command).name if command else "",
    }
    if not command:
        return {
            **projection,
            "status": "blocked",
            "blocking": True,
            "readiness_kind": "command_required",
            "next_action_kind": "configure_executor_command",
            "available_executor_kinds": [],
        }

    try:
        normalize_alignment_executor_settings(request)
    except LooporaError:
        return {
            **projection,
            "status": "blocked",
            "blocking": True,
            "readiness_kind": "invalid_configuration",
            "next_action_kind": "review_executor_configuration",
            "available_executor_kinds": [],
        }

    try:
        runtime = executor_factory()
    except Exception as exc:  # noqa: BLE001 - readiness must not expose factory internals.
        log_exception(
            logger,
            "executor.readiness.runtime_unavailable",
            "Executor runtime could not be initialized during readiness check",
            error=exc,
            level=logging.INFO,
            executor_kind=executor_kind,
        )
        return {
            **projection,
            "status": "blocked",
            "blocking": True,
            "readiness_kind": "runtime_unavailable",
            "next_action_kind": "review_executor_runtime",
            "available_executor_kinds": [],
        }
    if not isinstance(runtime, RealCodexExecutor):
        return {
            **projection,
            "status": "ready",
            "blocking": False,
            "readiness_kind": "managed_runtime",
            "next_action_kind": "start_or_continue_conversation",
            "available_executor_kinds": [],
        }

    available_executor_kinds = _available_preset_executor_kinds()
    if shutil.which(command):
        return {
            **projection,
            "status": "ready",
            "blocking": False,
            "readiness_kind": "executable_available",
            "next_action_kind": "start_or_continue_conversation",
            "available_executor_kinds": available_executor_kinds,
        }
    return {
        **projection,
        "status": "blocked",
        "blocking": True,
        "readiness_kind": "executable_not_found",
        "next_action_kind": "choose_available_executor_or_command",
        "available_executor_kinds": available_executor_kinds,
    }


def _available_preset_executor_kinds() -> list[str]:
    return [
        str(profile["key"])
        for profile in list_executor_profiles()
        if str(profile.get("cli_name") or "") and shutil.which(str(profile["cli_name"]))
    ]
