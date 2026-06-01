from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_native_step_contracts import agent_native_evidence_rules, agent_native_todo_contract
from loopora.agent_native_iteration_repair import agent_native_step_view_iteration_repair_context
from loopora.agent_native_judgment_contract import agent_native_step_view_judgment_contract
from loopora.agent_native_step_continuation import agent_native_step_view_continuation_context
from loopora.agent_native_required_coverage import agent_native_required_coverage
from loopora.agent_native_submit_hints import (
    agent_native_submit_command,
    agent_native_submit_hint_with_scoped_result_paths,
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
    submit_hint = agent_native_submit_hint_with_scoped_result_paths(submit_hint, step_view, run_id=run_id, step_id=step_id)
    result_file = str(submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path") or "").strip()
    if not result_file:
        template_path = str(submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or "").strip()
        if template_path.endswith(".result.template.json"):
            result_file = template_path[: -len(".result.template.json")] + ".result.json"
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
