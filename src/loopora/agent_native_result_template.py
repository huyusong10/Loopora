from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.agent_native_role_dispatch import agent_native_template_role_dispatch
from loopora.service_agent_native_contracts import (
    _agent_native_result_scaffold_from_schema,
    _agent_native_template_coverage_targets,
)
from loopora.service_types import LooporaError
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import write_json


def write_agent_native_step_contract_files(capsule: dict[str, Any]) -> None:
    step_contract_path_text = str(capsule.get("step_contract_absolute_path") or capsule.get("step_contract_path") or "").strip()
    legacy_capsule_path_text = str(capsule.get("capsule_absolute_path") or capsule.get("capsule_path") or "").strip()
    if not step_contract_path_text and not legacy_capsule_path_text:
        raise LooporaError("agent-native step contract path is required")
    step_contract_paths = [Path(path) for path in (step_contract_path_text, legacy_capsule_path_text) if path]
    written_paths: set[Path] = set()
    for step_contract_path in step_contract_paths:
        if step_contract_path in written_paths:
            continue
        write_json(step_contract_path, capsule)
        written_paths.add(step_contract_path)

    submit_hint = capsule.get("submit_hint") if isinstance(capsule.get("submit_hint"), dict) else {}
    template_path_text = str(submit_hint.get("result_template_absolute_path") or "").strip()
    if not template_path_text:
        raise LooporaError("agent-native result template path is required")
    template_path = Path(template_path_text)
    write_json(template_path, agent_native_result_template(capsule))


def agent_native_result_template(capsule: dict[str, Any]) -> dict[str, Any]:
    dispatch = capsule.get("role_dispatch") if isinstance(capsule.get("role_dispatch"), dict) else {}
    target_agent = str(dispatch.get("target_agent") or "").strip()
    output_schema = dict(capsule.get("output_schema") or {}) if isinstance(capsule.get("output_schema"), dict) else {}
    return {
        "loopora_host_dispatch": _agent_native_template_host_dispatch(capsule, target_agent=target_agent),
        "loopora_result_contract": _agent_native_result_contract(capsule, dispatch=dispatch, output_schema=output_schema),
        "result": _agent_native_result_scaffold_from_schema(output_schema),
    }


def _agent_native_result_contract(
    capsule: dict[str, Any],
    *,
    dispatch: dict[str, Any],
    output_schema: dict[str, Any],
) -> dict[str, Any]:
    coverage_targets = _agent_native_template_coverage_targets(capsule)
    result_contract: dict[str, Any] = {
        "ignored_on_submit": True,
        "result_must_match_output_schema": True,
        "result_is_schema_shaped_scaffold": True,
        "result_scaffold_uses_null_placeholders": True,
        "replace_null_placeholders_before_submit": True,
        "remove_optional_placeholders_if_unused": True,
        "array_placeholders_show_item_shape": True,
        "step_id": str(capsule.get("step_id") or ""),
        "role": dict(capsule.get("role") or {}) if isinstance(capsule.get("role"), dict) else {},
        "action_policy": dict(capsule.get("action_policy") or {}) if isinstance(capsule.get("action_policy"), dict) else {},
        "required_coverage": dict(capsule.get("required_coverage") or {})
        if isinstance(capsule.get("required_coverage"), dict)
        else {},
        "coverage_target_ids": [str(item["id"]) for item in coverage_targets],
        "coverage_targets": coverage_targets,
        "known_evidence_ids": list(
            dict.fromkeys(str(item) for item in list(capsule.get("known_evidence_ids") or []) if isinstance(item, str))
        ),
        "known_evidence_refs": [dict(item) for item in list(capsule.get("known_evidence_refs") or []) if isinstance(item, dict)],
        "evidence_ref_contract": dict(capsule.get("evidence_ref_contract") or {})
        if isinstance(capsule.get("evidence_ref_contract"), dict)
        else {},
        "evidence_rules": [dict(item) for item in list(capsule.get("evidence_rules") or []) if isinstance(item, dict)],
        "role_dispatch": agent_native_template_role_dispatch(dispatch),
        "output_schema": output_schema,
    }
    submit_hint = capsule.get("submit_hint") if isinstance(capsule.get("submit_hint"), dict) else {}
    _add_submit_hint_contract_fields(result_contract, submit_hint)
    iteration_repair = dict(capsule.get("iteration_repair") or {}) if isinstance(capsule.get("iteration_repair"), dict) else {}
    if iteration_repair.get("active") is True:
        result_contract["iteration_repair"] = iteration_repair
    native_todo = capsule.get("native_todo") if isinstance(capsule.get("native_todo"), dict) else {}
    if native_todo:
        result_contract["native_todo"] = native_todo
    native_trace_contract = dispatch.get("native_trace_contract") if isinstance(dispatch.get("native_trace_contract"), dict) else {}
    if native_trace_contract:
        result_contract["native_trace_contract"] = native_trace_contract
    return result_contract


def _add_submit_hint_contract_fields(result_contract: dict[str, Any], submit_hint: dict[str, Any]) -> None:
    result_file_to_write = str(submit_hint.get("result_file_absolute_path") or submit_hint.get("result_file_path") or "").strip()
    if result_file_to_write:
        result_contract["result_file_to_write"] = result_file_to_write
    submit_command = str(submit_hint.get("command") or "").strip()
    if submit_command:
        result_contract["submit_command"] = submit_command
    result_template_path = str(
        submit_hint.get("result_template_absolute_path") or submit_hint.get("result_template_path") or ""
    ).strip()
    if result_template_path:
        result_contract["result_template_path"] = result_template_path


def _agent_native_template_host_dispatch(capsule: dict[str, Any], *, target_agent: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "adapter": str(capsule.get("adapter") or ""),
        "run_id": str(capsule.get("run_id") or ""),
        "iter": structured_non_negative_int(capsule.get("iter")),
        "step_id": str(capsule.get("step_id") or ""),
        "step_order": structured_non_negative_int(capsule.get("step_order")),
        "target_agent": target_agent,
        "actual_agent": target_agent,
        "dispatch_mode": "host_subagent",
        "inline": False,
        "native_tool_name": "",
        "native_trace_ref": "",
        "native_trace": {
            "available": False,
            "tool_name": "",
            "tool_call_id": "",
            "subagent_run_id": "",
            "event_ref": "",
            "notes": "",
        },
        "attestation": "The host invoked the named Loopora role agent for this step.",
    }
