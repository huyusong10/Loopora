from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loopora.agent_native_step_contracts import agent_native_evidence_rules, agent_native_todo_contract
from loopora.agent_native_context_artifacts import agent_native_context_artifact_refs
from loopora.agent_native_iteration_repair import agent_native_step_view_iteration_repair_context
from loopora.agent_native_judgment_contract import agent_native_step_view_judgment_contract
from loopora.agent_native_step_continuation import agent_native_step_view_continuation_context
from loopora.agent_native_evidence_refs import agent_native_step_view_known_evidence_ids
from loopora.agent_native_evidence_contracts import agent_native_coverage_targets_from_judgment_contract
from loopora.agent_native_required_coverage import agent_native_required_coverage
from loopora.agent_native_role_dispatch import agent_native_role_dispatch
from loopora.agent_native_step_view_refresh import refresh_agent_native_step_view_with_judgment_contract as refresh_agent_native_step_view_with_judgment_contract
from loopora.agent_native_submit_hints import agent_native_result_artifact_stem, agent_native_submit_command
from loopora.agent_native_known_evidence_refs import _agent_native_compact_known_evidence_refs
from loopora.run_artifacts import RunArtifactLayout


@dataclass(frozen=True)
class AgentNativeStepViewRequest:
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
    step_instruction_context: dict[str, Any] | None = None
    entry_source: str = ""


def agent_native_step_view(request: AgentNativeStepViewRequest) -> dict[str, Any]:
    context_path = request.layout.step_instruction_context_path(request.iter_id, request.step_order, request.step["id"])
    agent_step_view_path = request.layout.step_agent_view_path(request.iter_id, request.step_order, request.step["id"])
    step_contract_path = request.layout.step_contract_path(request.iter_id, request.step_order, request.step["id"])
    output_path = request.layout.step_output_raw_path(request.iter_id, request.step_order, request.step["id"])
    result_outbox_dir = request.layout.workdir_path / ".loopora" / "agent_outbox" / request.adapter
    result_artifact_stem = agent_native_result_artifact_stem(
        run_id=str(request.run["id"]),
        iter_id=request.iter_id,
        step_order=request.step_order,
        step_id=str(request.step["id"]),
    )
    result_template_path = result_outbox_dir / f"{result_artifact_stem}.result.template.json"
    result_file_path = result_outbox_dir / f"{result_artifact_stem}.result.json"
    known_evidence_ids = agent_native_step_view_known_evidence_ids(
        known_evidence_ids=request.known_evidence_ids,
        layout=request.layout,
    )
    normalized_entry_source = str(request.entry_source or "").strip()
    role_dispatch = agent_native_role_dispatch(
        adapter=request.adapter,
        role_archetype=str(request.role["archetype"]),
        workdir_path=request.layout.workdir_path,
    )
    target_agent = str(role_dispatch.get("target_agent") or "")
    step_context = request.step_instruction_context
    judgment_contract = agent_native_step_view_judgment_contract(request.run, step_context)
    coverage_targets = agent_native_coverage_targets_from_judgment_contract(judgment_contract)
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
        "required_coverage": agent_native_required_coverage(step_context),
        "judgment_contract": judgment_contract,
        "coverage_target_ids": [str(item["id"]) for item in coverage_targets],
        "coverage_targets": coverage_targets,
        "continuation": agent_native_step_view_continuation_context(step_context),
        "iteration_repair": agent_native_step_view_iteration_repair_context(step_context),
        "context_artifacts": agent_native_context_artifact_refs(step_context),
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
        "agent_step_view_path": request.layout.relative(agent_step_view_path),
        "agent_step_view_absolute_path": str(agent_step_view_path.resolve()),
        "step_contract_path": request.layout.relative(step_contract_path),
        "step_contract_absolute_path": str(step_contract_path.resolve()),
        "result_output_path": request.layout.relative(output_path),
        "submit_hint": {
            "command": agent_native_submit_command(
                adapter=request.adapter,
                run_id=str(request.run["id"]),
                step_id=str(request.step["id"]),
                entry_source=normalized_entry_source,
                result_file=str(result_file_path.resolve()),
            ),
            "result_file_contract": "Result file must contain one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit.",
            "result_outbox_dir": request.layout.workspace_relative(result_outbox_dir),
            "result_outbox_absolute_dir": str(result_outbox_dir.resolve()),
            "result_file_path": request.layout.workspace_relative(result_file_path),
            "result_file_absolute_path": str(result_file_path.resolve()),
            "result_template_path": request.layout.workspace_relative(result_template_path),
            "result_template_absolute_path": str(result_template_path.resolve()),
        },
        "known_evidence_ids": known_evidence_ids,
        "known_evidence_refs": _agent_native_compact_known_evidence_refs(known_evidence_ids, step_context),
        "known_evidence_count": len(known_evidence_ids),
    }
