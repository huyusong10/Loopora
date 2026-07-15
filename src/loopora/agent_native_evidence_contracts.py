from __future__ import annotations

from typing import Any


from loopora.utils import coerced_int

AGENT_NATIVE_STEP_VIEW_KEY = "agent_step_view"

def agent_native_active_step_is_stale(active: dict[str, Any], current_step_projection: dict[str, Any]) -> bool:
    source_sequence = coerced_int(current_step_projection.get("source_sequence"))
    if source_sequence <= 0:
        return False
    step_view = agent_native_active_step_view(active)
    active_step = active.get("step") if isinstance(active.get("step"), dict) else {}
    active_step_id = str(active_step.get("id") or step_view.get("step_id") or "").strip()
    active_iter = coerced_int(_first_present(active.get("iter_id"), step_view.get("iter")), default=-1)
    active_adapter = str(step_view.get("adapter") or active.get("adapter") or "").strip()
    projected_step_id = str(current_step_projection.get("step_id") or "").strip()
    projected_iter = coerced_int(current_step_projection.get("iteration"), default=-1)
    if not current_step_projection.get("claimable"):
        return bool(active_step_id)
    if active_step_id != projected_step_id or active_iter != projected_iter:
        return True
    pending_actor = current_step_projection.get("pending_actor") if isinstance(current_step_projection.get("pending_actor"), dict) else {}
    projected_adapter = str(pending_actor.get("adapter") or pending_actor.get("id") or "").strip()
    return bool(active_adapter and projected_adapter and active_adapter != projected_adapter)

def agent_native_active_step_view(active: dict[str, Any]) -> dict[str, Any]:
    step_view = agent_native_active_step_view_payload(active)
    return dict(step_view) if isinstance(step_view, dict) else {}

def agent_native_active_step_view_payload(active: dict[str, Any]) -> object:
    return active.get(AGENT_NATIVE_STEP_VIEW_KEY)

def agent_native_active_step_view_fields(step_view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {AGENT_NATIVE_STEP_VIEW_KEY: step_view}

def _first_present(*values: object) -> object:
    return next((value for value in values if value is not None and value != ""), None)



def _agent_native_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _agent_native_output_evidence_refs(output: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    refs.extend(_agent_native_string_list(output.get("evidence_refs")))
    for item in list(output.get("coverage_results") or []):
        if isinstance(item, dict):
            refs.extend(_agent_native_string_list(item.get("evidence_refs")))
    return list(dict.fromkeys(refs))


def _agent_native_known_evidence_ids(active: dict, step_instruction_context: dict) -> set[str]:
    step_view = agent_native_active_step_view(active)
    if isinstance(step_view.get("known_evidence_ids"), list):
        return set(_agent_native_string_list(step_view.get("known_evidence_ids")))
    evidence = (
        step_instruction_context.get("evidence") if isinstance(step_instruction_context.get("evidence"), dict) else {}
    )
    return set(_agent_native_string_list(evidence.get("known_ids")))


def agent_native_unknown_evidence_refs(
    output: dict[str, Any],
    *,
    active: dict,
    step_instruction_context: dict,
) -> list[str]:
    known_ids = _agent_native_known_evidence_ids(active, step_instruction_context)
    return [item for item in _agent_native_output_evidence_refs(output) if item not in known_ids]


def _agent_native_output_coverage_target_ids(output: dict[str, Any]) -> list[str]:
    target_ids: list[str] = []
    for item in list(output.get("coverage_results") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        if target_id:
            target_ids.append(target_id)
    return list(dict.fromkeys(target_ids))


def _agent_native_output_coverage_results(output: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in list(output.get("coverage_results") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        status = str(item.get("status") or "").strip()
        if not target_id or not status:
            continue
        result: dict[str, Any] = {"target_id": target_id, "status": status}
        evidence_refs = _agent_native_string_list(item.get("evidence_refs"))
        if evidence_refs:
            result["evidence_refs"] = evidence_refs
        note = str(item.get("note") or "").strip()
        if note:
            result["note"] = note
        results.append(result)
    return results


def _agent_native_step_view_coverage_target_ids(active: dict[str, Any]) -> set[str]:
    step_view = agent_native_active_step_view(active)
    judgment_contract = step_view.get("judgment_contract") if isinstance(step_view.get("judgment_contract"), dict) else {}
    target_ids: set[str] = set()
    for item in list(judgment_contract.get("coverage_targets") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("id") or item.get("target_id") or "").strip()
        if target_id:
            target_ids.add(target_id)
    return target_ids


def _agent_native_unknown_coverage_target_ids(output: dict[str, Any], *, active: dict[str, Any]) -> list[str]:
    known_target_ids = _agent_native_step_view_coverage_target_ids(active)
    return [target_id for target_id in _agent_native_output_coverage_target_ids(output) if target_id not in known_target_ids]


def agent_native_coverage_targets_from_judgment_contract(judgment_contract: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for item in list(judgment_contract.get("coverage_targets") or []):
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("id") or item.get("target_id") or "").strip()
        if not target_id:
            continue
        targets.append(
            {
                "id": target_id,
                "kind": str(item.get("kind") or "").strip(),
                "required": bool(item.get("required")),
                "text": str(item.get("text") or item.get("label") or "").strip(),
            }
        )
    return targets


def _agent_native_step_view_coverage_targets(step_view: dict[str, Any]) -> list[dict[str, Any]]:
    judgment_contract = step_view.get("judgment_contract") if isinstance(step_view.get("judgment_contract"), dict) else {}
    return agent_native_coverage_targets_from_judgment_contract(judgment_contract)


AGENT_NATIVE_WORKSPACE_ARTIFACT_FIELDS = ("changed_files", "generated_files", "proof_files", "proof_artifacts", "artifact_paths")
