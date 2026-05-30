from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.agent_native_capsule_context import (
    agent_native_capsule_continuation_context,
    agent_native_capsule_iteration_repair_context,
    agent_native_capsule_judgment_contract,
    agent_native_evidence_rules,
    agent_native_required_coverage,
    agent_native_todo_contract,
)
from loopora.agent_native_role_dispatch import agent_native_role_dispatch
from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from loopora.service_agent_native_contracts import (
    _agent_native_compact_known_evidence_refs,
    _agent_native_result_artifact_stem,
    _agent_native_submit_hint_with_scoped_result_paths,
    agent_native_submit_command,
)
from loopora.service_types import LooporaError


@dataclass(frozen=True)
class AgentNativeCapsuleRequest:
    adapter: str
    run: dict[str, Any]
    layout: RunArtifactLayout
    iter_id: int
    step: dict[str, Any]
    step_order: int
    role: dict[str, Any]
    runtime_role: str
    prompt: str
    output_schema: dict[str, Any]
    known_evidence_ids: list[str] | None = None
    context_packet: dict[str, Any] | None = None
    entry_source: str = ""


def agent_native_capsule(request: AgentNativeCapsuleRequest) -> dict[str, Any]:
    context_path = request.layout.step_context_path(request.iter_id, request.step_order, request.step["id"])
    capsule_path = request.layout.step_capsule_path(request.iter_id, request.step_order, request.step["id"])
    step_contract_path = request.layout.step_contract_path(request.iter_id, request.step_order, request.step["id"])
    output_path = request.layout.step_output_raw_path(request.iter_id, request.step_order, request.step["id"])
    result_outbox_dir = request.layout.workdir_path / ".loopora" / "agent_outbox" / request.adapter
    result_artifact_stem = _agent_native_result_artifact_stem(
        run_id=str(request.run["id"]),
        iter_id=request.iter_id,
        step_order=request.step_order,
        step_id=str(request.step["id"]),
    )
    result_template_path = result_outbox_dir / f"{result_artifact_stem}.result.template.json"
    result_file_path = result_outbox_dir / f"{result_artifact_stem}.result.json"
    known_evidence_ids = _agent_native_capsule_known_evidence_ids(request)
    normalized_entry_source = str(request.entry_source or "").strip()
    role_dispatch = agent_native_role_dispatch(
        adapter=request.adapter,
        role_archetype=str(request.role["archetype"]),
        workdir_path=request.layout.workdir_path,
    )
    target_agent = str(role_dispatch.get("target_agent") or "")
    return {
        "execution_plane": "agent_native",
        "adapter": request.adapter,
        "entry_source": normalized_entry_source,
        "run_id": request.run["id"],
        "run_path": f"/runs/{request.run['id']}",
        "iter": request.iter_id,
        "step_id": request.step["id"],
        "step_order": request.step_order,
        "parallel_group": str(request.step.get("parallel_group") or ""),
        "role": {
            "id": request.role["id"],
            "name": request.role["name"],
            "archetype": request.role["archetype"],
            "prompt_ref": str(request.role.get("prompt_ref") or ""),
            "posture_notes": str(request.role.get("posture_notes") or "").strip(),
            "runtime_role": request.runtime_role,
        },
        "role_dispatch": role_dispatch,
        "native_todo": agent_native_todo_contract(step_id=str(request.step["id"]), target_agent=target_agent),
        "inputs": dict(request.step.get("inputs") or {}) if isinstance(request.step.get("inputs"), dict) else {},
        "action_policy": dict(request.step.get("action_policy") or {}),
        "required_coverage": agent_native_required_coverage(request.context_packet),
        "judgment_contract": agent_native_capsule_judgment_contract(request.run, request.context_packet),
        "continuation": agent_native_capsule_continuation_context(request.context_packet),
        "iteration_repair": agent_native_capsule_iteration_repair_context(request.context_packet),
        "prompt": request.prompt,
        "output_schema": request.output_schema,
        "evidence_rules": agent_native_evidence_rules(str(request.role["archetype"])),
        "evidence_ref_contract": {
            "allowed_ids_field": "known_evidence_ids",
            "unknown_ids_are_blocking": True,
            "must_copy_exact_ids": True,
        },
        "context_path": request.layout.relative(context_path),
        "context_absolute_path": str(context_path.resolve()),
        "step_contract_path": request.layout.relative(step_contract_path),
        "step_contract_absolute_path": str(step_contract_path.resolve()),
        "capsule_path": request.layout.relative(capsule_path),
        "capsule_absolute_path": str(capsule_path.resolve()),
        "result_output_path": request.layout.relative(output_path),
        "submit_hint": {
            "command": agent_native_submit_command(
                adapter=request.adapter,
                run_id=str(request.run["id"]),
                step_id=str(request.step["id"]),
                entry_source=normalized_entry_source,
                result_file=str(result_file_path.resolve()),
            ),
            "result_file_contract": "Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit.",
            "result_outbox_dir": request.layout.workspace_relative(result_outbox_dir),
            "result_outbox_absolute_dir": str(result_outbox_dir.resolve()),
            "result_file_path": request.layout.workspace_relative(result_file_path),
            "result_file_absolute_path": str(result_file_path.resolve()),
            "result_template_path": request.layout.workspace_relative(result_template_path),
            "result_template_absolute_path": str(result_template_path.resolve()),
        },
        "known_evidence_ids": known_evidence_ids,
        "known_evidence_refs": _agent_native_compact_known_evidence_refs(known_evidence_ids, request.context_packet),
        "known_evidence_count": len(known_evidence_ids),
    }


def refresh_agent_native_capsule_with_judgment_contract(
    run: dict[str, Any],
    capsule: object,
    *,
    context_packet: object = None,
) -> dict[str, Any]:
    if not isinstance(capsule, dict):
        raise LooporaError("agent-native active step contract is invalid")
    normalized = dict(capsule)
    normalized["judgment_contract"] = agent_native_capsule_judgment_contract(run, context_packet)
    normalized["required_coverage"] = agent_native_required_coverage(context_packet)
    normalized["continuation"] = agent_native_capsule_continuation_context(context_packet)
    normalized["iteration_repair"] = agent_native_capsule_iteration_repair_context(context_packet)
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
        _agent_native_compact_known_evidence_refs(known_evidence_ids, context_packet) if isinstance(known_evidence_ids, list) else []
    )
    return normalized


def agent_native_context_packet_with_coverage(context_packet: object, coverage: dict[str, Any]) -> object:
    if not isinstance(context_packet, dict):
        return context_packet
    iteration = dict(context_packet.get("iteration") or {}) if isinstance(context_packet.get("iteration"), dict) else {}
    refreshed_iteration = {
        **iteration,
        "coverage_status": coverage["status"],
        "covered_check_count": coverage["covered_check_count"],
        "missing_check_count": coverage["missing_check_count"],
        "covered_check_ids": list(coverage["covered_check_ids"]),
        "missing_check_ids": list(coverage["missing_check_ids"]),
        "target_count": coverage["target_count"],
        "covered_target_count": coverage["covered_target_count"],
        "weak_target_count": coverage["weak_target_count"],
        "missing_target_count": coverage["missing_target_count"],
        "blocked_target_count": coverage["blocked_target_count"],
        "coverage_top_gaps": [dict(item) for item in list(coverage["top_gaps"]) if isinstance(item, dict)],
    }
    refreshed_packet = dict(context_packet)
    refreshed_packet["iteration"] = refreshed_iteration
    return refreshed_packet


def _agent_native_capsule_known_evidence_ids(request: AgentNativeCapsuleRequest) -> list[str]:
    if request.known_evidence_ids is not None:
        return list(dict.fromkeys(str(item) for item in request.known_evidence_ids if str(item).strip()))
    return list(
        dict.fromkeys(
            str(item.get("id"))
            for item in read_jsonl(request.layout.evidence_ledger_path)
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        )
    )


def _refresh_agent_native_submit_hint(capsule: dict[str, Any]) -> None:
    submit_hint = dict(capsule.get("submit_hint") or {}) if isinstance(capsule.get("submit_hint"), dict) else {}
    if not submit_hint:
        return
    adapter = str(capsule.get("adapter") or "").strip()
    run_id = str(capsule.get("run_id") or "").strip()
    step_id = str(capsule.get("step_id") or "").strip()
    if not adapter or not run_id or not step_id:
        return
    submit_hint = _agent_native_submit_hint_with_scoped_result_paths(submit_hint, capsule, run_id=run_id, step_id=step_id)
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
        entry_source=str(capsule.get("entry_source") or "").strip(),
        result_file=result_file or "RESULT_JSON_PATH",
    )
    capsule["submit_hint"] = submit_hint


def _refresh_agent_native_role_dispatch_availability(capsule: dict[str, Any]) -> None:
    dispatch = dict(capsule.get("role_dispatch") or {}) if isinstance(capsule.get("role_dispatch"), dict) else {}
    if not dispatch:
        return
    config_path = str(dispatch.get("target_agent_config_absolute_path") or "").strip()
    if not config_path:
        config_path = str(dispatch.get("target_agent_config_path") or "").strip()
    if not config_path:
        dispatch["target_agent_config_exists"] = False
        capsule["role_dispatch"] = dispatch
        return
    dispatch["target_agent_config_exists"] = Path(config_path).expanduser().exists()
    capsule["role_dispatch"] = dispatch
