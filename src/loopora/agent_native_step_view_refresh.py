from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_native_context_artifacts import agent_native_context_artifact_refs
from loopora.agent_native_step_contracts import agent_native_evidence_rules, agent_native_todo_contract
from loopora.agent_native_iteration_repair import agent_native_step_view_iteration_repair_context
from loopora.agent_native_judgment_contract import agent_native_step_view_judgment_contract
from loopora.agent_native_step_continuation import agent_native_step_view_continuation_context
from loopora.agent_native_required_coverage import agent_native_required_coverage
from loopora.agent_native_submit_hints import (
    agent_native_submit_command,
    agent_native_submit_hint_with_scoped_result_paths,
    agent_native_workdir_from_loopora_path,
)
from loopora.agent_native_known_evidence_refs import _agent_native_compact_known_evidence_refs
from loopora.service_types import LooporaError


def refresh_agent_native_step_view_with_judgment_contract(
    run: dict[str, Any],
    step_view: object,
    *,
    step_instruction_context: object = None,
) -> dict[str, Any]:
    if not isinstance(step_view, dict):
        raise LooporaError("agent-native active step contract is invalid")
    step_context = step_instruction_context
    normalized = dict(step_view)
    normalized["judgment_contract"] = agent_native_step_view_judgment_contract(run, step_context)
    normalized["required_coverage"] = agent_native_required_coverage(step_context)
    normalized["continuation"] = agent_native_step_view_continuation_context(step_context)
    normalized["iteration_repair"] = agent_native_step_view_iteration_repair_context(step_context)
    normalized["context_artifacts"] = agent_native_context_artifact_refs(step_context)
    role = normalized.get("role") if isinstance(normalized.get("role"), dict) else {}
    archetype = str(role.get("archetype") or "").strip()
    if archetype:
        normalized["evidence_rules"] = agent_native_evidence_rules(archetype)
    _refresh_agent_native_submit_hint(normalized)
    _refresh_agent_native_role_dispatch_availability(normalized)
    normalized["native_todo"] = agent_native_todo_contract(
        step_id=str(normalized.get("step_id") or ""),
        target_agent=str((normalized.get("role_dispatch") or {}).get("target_agent") or "")
        if isinstance(normalized.get("role_dispatch"), dict)
        else "",
    )
    known_evidence_ids = normalized.get("known_evidence_ids")
    if isinstance(known_evidence_ids, list):
        known_evidence_ids = list(dict.fromkeys(str(item) for item in known_evidence_ids if isinstance(item, str)))
        normalized["known_evidence_ids"] = known_evidence_ids
    normalized["known_evidence_count"] = len(known_evidence_ids) if isinstance(known_evidence_ids, list) else 0
    normalized["known_evidence_refs"] = (
        _agent_native_compact_known_evidence_refs(known_evidence_ids, step_context) if isinstance(known_evidence_ids, list) else []
    )
    return normalized


def _refresh_agent_native_submit_hint(step_view: dict[str, Any]) -> None:
    submit_hint = dict(step_view.get("submit_hint") or {}) if isinstance(step_view.get("submit_hint"), dict) else {}
    if not submit_hint:
        return
    adapter = str(step_view.get("adapter") or "").strip()
    run_id = str(step_view.get("run_id") or "").strip()
    step_id = str(step_view.get("step_id") or "").strip()
    if not adapter or not run_id or not step_id:
        return
    workdir = _agent_native_step_view_workdir(step_view, submit_hint)
    _restore_agent_native_absolute_submit_hint_paths(submit_hint, workdir=workdir)
    submit_hint = agent_native_submit_hint_with_scoped_result_paths(submit_hint, step_view, run_id=run_id, step_id=step_id)
    workdir = _agent_native_step_view_workdir(step_view, submit_hint) or workdir
    result_file = str(submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path") or "").strip()
    if not result_file:
        template_path = str(submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or "").strip()
        if template_path.endswith(".result.template.json"):
            result_file = template_path[: -len(".result.template.json")] + ".result.json"
    absolute_result_file = _agent_native_absolute_artifact_path(result_file, workdir=workdir)
    if absolute_result_file:
        result_file = absolute_result_file
    if result_file and result_file != "RESULT_JSON_PATH":
        if Path(result_file).is_absolute():
            submit_hint["result_file_absolute_path"] = result_file
        else:
            submit_hint["result_file_path"] = result_file
    submit_hint["command"] = agent_native_submit_command(
        adapter=adapter,
        run_id=run_id,
        step_id=step_id,
        entry_source=str(step_view.get("entry_source") or "").strip(),
        result_file=result_file or "RESULT_JSON_PATH",
    )
    step_view["submit_hint"] = submit_hint


def _agent_native_step_view_workdir(step_view: dict[str, Any], submit_hint: dict[str, Any]) -> str:
    for value in (
        submit_hint.get("result_file_absolute_path"),
        submit_hint.get("result_template_absolute_path"),
        submit_hint.get("result_outbox_absolute_dir"),
        step_view.get("context_absolute_path"),
        step_view.get("agent_step_view_absolute_path"),
        step_view.get("step_contract_absolute_path"),
    ):
        workdir = agent_native_workdir_from_loopora_path(value)
        if workdir:
            return workdir
    return ""


def _restore_agent_native_absolute_submit_hint_paths(submit_hint: dict[str, Any], *, workdir: str) -> None:
    if not workdir:
        return
    for relative_key, absolute_key in (
        ("result_outbox_dir", "result_outbox_absolute_dir"),
        ("result_template_path", "result_template_absolute_path"),
        ("result_file_path", "result_file_absolute_path"),
    ):
        if str(submit_hint.get(absolute_key) or "").strip():
            continue
        absolute_path = _agent_native_absolute_artifact_path(submit_hint.get(relative_key), workdir=workdir)
        if absolute_path:
            submit_hint[absolute_key] = absolute_path


def _agent_native_absolute_artifact_path(value: object, *, workdir: str) -> str:
    text = str(value or "").strip()
    if not text or text == "RESULT_JSON_PATH":
        return ""
    try:
        path = Path(text).expanduser()
    except (OSError, ValueError):
        return ""
    if path.is_absolute():
        return str(path)
    if not workdir or any(part == ".." for part in path.parts):
        return ""
    try:
        return str((Path(workdir) / path).resolve())
    except OSError:
        return str(Path(workdir) / path)


def _refresh_agent_native_role_dispatch_availability(step_view: dict[str, Any]) -> None:
    dispatch = dict(step_view.get("role_dispatch") or {}) if isinstance(step_view.get("role_dispatch"), dict) else {}
    if not dispatch:
        return
    config_path = str(dispatch.get("target_agent_config_absolute_path") or "").strip()
    if not config_path:
        config_path = str(dispatch.get("target_agent_config_path") or "").strip()
    if not config_path:
        dispatch["target_agent_config_exists"] = False
        step_view["role_dispatch"] = dispatch
        return
    dispatch["target_agent_config_exists"] = Path(config_path).expanduser().exists()
    step_view["role_dispatch"] = dispatch
