from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loopora.cli_agent_submit_repair_results import _active_agent_native_step_view
from loopora.service import LooporaError


def read_result_json_with_auto_repair(
    path: Path,
    *,
    service,
    run_id: str = "",
    workdir: Path | None = None,
) -> tuple[dict, dict, list[str]]:
    payload = _read_json_object(path)
    result, host_dispatch = _strict_result_parts(payload)
    if result is not None and host_dispatch is not None:
        active_template = _active_template_context(
            service,
            run_id=_payload_run_id(payload) or str(run_id or "").strip(),
            workdir=workdir,
        )
        actions = _template_path_actions(path, active_template)
        return result, host_dispatch, actions

    active_template = _active_template_context(
        service,
        run_id=_payload_run_id(payload) or str(run_id or "").strip(),
        workdir=workdir,
    )
    repaired = _repair_with_active_template(payload, active_template)
    if repaired:
        result, host_dispatch, actions = repaired
        actions.extend(_template_path_actions(path, active_template))
        return result, host_dispatch, _dedupe(actions)

    return _strict_result_json(payload)


def _read_json_object(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LooporaError(f"result file is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LooporaError("result file must contain one JSON object")
    return payload


def _strict_result_json(payload: dict) -> tuple[dict, dict, list[str]]:
    if "loopora_host_dispatch" in payload or "result" in payload:
        host_dispatch = payload.get("loopora_host_dispatch")
        result = payload.get("result")
        if not isinstance(host_dispatch, dict):
            raise LooporaError("result wrapper must contain loopora_host_dispatch object")
        if not isinstance(result, dict):
            raise LooporaError("result wrapper must contain result object")
        return result, host_dispatch, []
    return payload, {}, []


def _strict_result_parts(payload: dict) -> tuple[dict | None, dict | None]:
    if "loopora_host_dispatch" not in payload and "result" not in payload:
        return None, None
    host_dispatch = payload.get("loopora_host_dispatch")
    result = payload.get("result")
    if isinstance(host_dispatch, dict) and isinstance(result, dict):
        return result, host_dispatch
    return None, None


def _repair_with_active_template(payload: dict, active_template: dict) -> tuple[dict, dict, list[str]] | None:
    template_dispatch = active_template.get("loopora_host_dispatch")
    if not isinstance(template_dispatch, dict) or not template_dispatch:
        return None
    if "loopora_host_dispatch" in payload and isinstance(payload.get("loopora_host_dispatch"), dict):
        return None
    if "result" in payload:
        result = payload.get("result")
        if not isinstance(result, dict):
            return None
        return result, dict(template_dispatch), ["restored_loopora_host_dispatch_from_active_template"]
    return dict(payload), dict(template_dispatch), ["wrapped_schema_result_with_active_template_dispatch"]


def _active_template_context(service, *, run_id: str, workdir: Path | None) -> dict[str, Any]:
    if not run_id or not hasattr(service, "get_run"):
        return {}
    try:
        active_step_view = _active_agent_native_step_view(service, run_id=run_id)
    except (AttributeError, LooporaError):
        return {}
    return _active_template_context_from_step_view(active_step_view, workdir=workdir)


def _active_template_context_from_step_view(active_step_view: dict, *, workdir: Path | None) -> dict[str, Any]:
    submit_hint = active_step_view.get("submit_hint") if isinstance(active_step_view.get("submit_hint"), dict) else {}
    template_path = _active_template_path(submit_hint, workdir=workdir)
    if not template_path:
        return {}
    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(template, dict):
        return {}
    dispatch = template.get("loopora_host_dispatch")
    if not isinstance(dispatch, dict) or not _template_dispatch_matches_active_step_view(dispatch, active_step_view):
        return {}
    return {"path": template_path, "loopora_host_dispatch": dispatch}


def _active_template_path(submit_hint: dict, *, workdir: Path | None) -> Path | None:
    path_text = str(submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or "").strip()
    if not path_text:
        return None
    path = Path(path_text).expanduser()
    if not path.is_absolute() and workdir is not None:
        path = Path(workdir).expanduser() / path
    return path


def _template_dispatch_matches_active_step_view(dispatch: dict, active_step_view: dict) -> bool:
    checks = (
        ("run_id", "run_id"),
        ("step_id", "step_id"),
        ("adapter", "adapter"),
        ("iter", "iter"),
        ("step_order", "step_order"),
    )
    for dispatch_key, active_key in checks:
        active_value = active_step_view.get(active_key)
        if active_value in ("", None):
            continue
        if _text(dispatch.get(dispatch_key)) != _text(active_value):
            return False
    return True


def _payload_run_id(payload: dict) -> str:
    dispatch = payload.get("loopora_host_dispatch") if isinstance(payload.get("loopora_host_dispatch"), dict) else {}
    return str(dispatch.get("run_id") or "").strip()


def _template_path_actions(path: Path, active_template: dict) -> list[str]:
    template_path = active_template.get("path")
    if not isinstance(template_path, Path) or not _same_path(path, template_path):
        return []
    return ["accepted_filled_result_template_path_as_result_file"]


def _same_path(candidate: Path, reference: Path) -> bool:
    try:
        return candidate.expanduser().resolve() == reference.expanduser().resolve()
    except OSError:
        return str(candidate) == str(reference)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""
