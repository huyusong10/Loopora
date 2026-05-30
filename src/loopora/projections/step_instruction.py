from __future__ import annotations

from loopora.events.envelope import EventEnvelope
from loopora.events.replay import replay_run_snapshot
from loopora.kernel import ActionPolicy, EvidenceScope, RoleSpec, StepInstruction, StepOutputContract
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION, latest_event, latest_sequence


def agent_step_view_projection(instruction: StepInstruction) -> dict:
    return {
        "kind": "agent_step_view",
        "run_id": instruction.run_id,
        "step_id": instruction.step_id,
        "iteration": instruction.iteration,
        "role": _role_projection(instruction),
        "objective": instruction.objective,
        "contract_ref": instruction.contract_ref,
        "evidence_scope": {
            "target_ids": list(instruction.evidence_scope.target_ids),
            "instructions": instruction.evidence_scope.instructions,
        },
        "action_policy": {
            "workspace": instruction.action_policy.workspace,
            "can_finish_run": instruction.action_policy.can_finish_run,
            "can_spawn_parallel": instruction.action_policy.can_spawn_parallel,
        },
        "output_contract": {
            "require_summary": instruction.output_contract.require_summary,
            "require_evidence_claims": instruction.output_contract.require_evidence_claims,
            "require_artifact_refs": instruction.output_contract.require_artifact_refs,
        },
    }


def cli_step_summary_projection(instruction: StepInstruction) -> dict:
    return {
        "kind": "cli_step_summary",
        "run_id": instruction.run_id,
        "step_id": instruction.step_id,
        "iteration": instruction.iteration,
        "role_name": instruction.role.name,
        "role_archetype": instruction.role.archetype,
        "target_count": len(instruction.evidence_scope.target_ids),
        "can_finish_run": instruction.action_policy.can_finish_run,
    }


def web_current_step_projection(instruction: StepInstruction) -> dict:
    return {
        "kind": "web_current_step",
        "identity": {
            "run_id": instruction.run_id,
            "step_id": instruction.step_id,
            "iteration": instruction.iteration,
        },
        "role": _role_projection(instruction),
        "objective": instruction.objective,
        "evidence_target_ids": list(instruction.evidence_scope.target_ids),
        "can_finish_run": instruction.action_policy.can_finish_run,
    }


def headless_prompt_projection(instruction: StepInstruction) -> str:
    target_lines = "\n".join(f"- {target_id}" for target_id in instruction.evidence_scope.target_ids)
    return "\n".join(
        line
        for line in (
            f"Run: {instruction.run_id}",
            f"Step: {instruction.step_id}",
            f"Role: {instruction.role.name or instruction.role.id}",
            "",
            instruction.objective,
            "",
            "Evidence targets:",
            target_lines or "- none declared",
            "",
            f"Contract: {instruction.contract_ref}",
        )
        if line is not None
    )


def replay_step_surface_projection_bundle(events: list[EventEnvelope]) -> dict:
    source_sequence = latest_sequence(events)
    event = latest_event(events, "StepInstructionIssued")
    if event is None:
        return {
            "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
            "kind": "event_replayed_step_surfaces",
            "source_sequence": source_sequence,
            "available": False,
            "agent_step_view": {},
            "cli_step_summary": {},
            "web_current_step": {},
            "headless_prompt": "",
        }
    snapshot = replay_run_snapshot(events)
    if (
        snapshot.state.current_step_id != str(event.payload.get("step_id") or "")
        or snapshot.state.current_iteration != _safe_int(event.payload.get("iteration"))
        or snapshot.state.pending_actor is None
    ):
        return {
            "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
            "kind": "event_replayed_step_surfaces",
            "source_sequence": source_sequence,
            "available": False,
            "agent_step_view": {},
            "cli_step_summary": {},
            "web_current_step": {},
            "headless_prompt": "",
        }
    instruction = _step_instruction_from_event(event)
    return {
        "schema_version": EVENT_REPLAY_PROJECTION_SCHEMA_VERSION,
        "kind": "event_replayed_step_surfaces",
        "source_sequence": source_sequence,
        "available": True,
        "agent_step_view": agent_step_view_projection(instruction),
        "cli_step_summary": cli_step_summary_projection(instruction),
        "web_current_step": web_current_step_projection(instruction),
        "headless_prompt": headless_prompt_projection(instruction),
    }


def _role_projection(instruction: StepInstruction) -> dict:
    return {
        "id": instruction.role.id,
        "name": instruction.role.name,
        "archetype": instruction.role.archetype,
        "responsibility": instruction.role.responsibility,
    }


def _step_instruction_from_event(event: EventEnvelope) -> StepInstruction:
    payload = event.payload
    role = _mapping(payload.get("role"))
    evidence_scope = _mapping(payload.get("evidence_scope"))
    action_policy = _mapping(payload.get("action_policy"))
    output_contract = _mapping(payload.get("output_contract"))
    return StepInstruction(
        run_id=str(payload.get("run_id") or event.aggregate_id),
        step_id=str(payload.get("step_id") or ""),
        iteration=_safe_int(payload.get("iteration")),
        role=RoleSpec(
            id=str(role.get("id") or ""),
            name=str(role.get("name") or ""),
            archetype=str(role.get("archetype") or ""),
            responsibility=str(role.get("responsibility") or ""),
        ),
        objective=str(payload.get("objective") or ""),
        contract_ref=str(payload.get("contract_ref") or ""),
        evidence_scope=EvidenceScope(
            target_ids=tuple(str(item) for item in list(evidence_scope.get("target_ids") or []) if str(item).strip()),
            instructions=str(evidence_scope.get("instructions") or ""),
        ),
        action_policy=ActionPolicy(
            workspace=str(action_policy.get("workspace") or "read_only"),
            can_finish_run=bool(action_policy.get("can_finish_run")),
            can_spawn_parallel=bool(action_policy.get("can_spawn_parallel")),
        ),
        output_contract=StepOutputContract(
            require_summary=bool(output_contract.get("require_summary")),
            require_evidence_claims=bool(output_contract.get("require_evidence_claims")),
            require_artifact_refs=bool(output_contract.get("require_artifact_refs")),
        ),
    )


def _mapping(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _safe_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
