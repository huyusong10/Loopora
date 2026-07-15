from __future__ import annotations

from pathlib import Path

from loopora.context_value_helpers import string_list as _string_list

from loopora.run_artifacts import RunArtifactLayout

def output_workspace_artifact_refs(layout: RunArtifactLayout, output: dict) -> list[dict[str, str]]:
    fields = (
        ("proof_files", "proof-file"),
        ("proof_artifacts", "proof-artifact"),
        ("artifact_paths", "artifact"),
        ("generated_files", "generated-file"),
        ("changed_files", "changed-file"),
    )
    refs: list[dict[str, str]] = []
    seen: set[str] = set()
    for field_name, label_prefix in fields:
        for value in _string_list(output.get(field_name)):
            ref = workspace_artifact_ref(layout, value, label_prefix=label_prefix)
            if not ref or ref["absolute_path"] in seen:
                continue
            refs.append(ref)
            seen.add(ref["absolute_path"])
    return refs[:20]

def workspace_artifact_ref(layout: RunArtifactLayout, value: str, *, label_prefix: str) -> dict[str, str] | None:
    cleaned = str(value or "").strip()
    if not cleaned or "\x00" in cleaned:
        return None
    candidate = Path(cleaned)
    workdir = layout.workdir_path.resolve()
    try:
        resolved = candidate.resolve() if candidate.is_absolute() else (workdir / candidate).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    try:
        workspace_path = resolved.relative_to(workdir).as_posix()
    except ValueError:
        return None
    try:
        if not resolved.exists():
            return None
    except OSError:
        return None
    return {
        "kind": "workspace",
        "label": f"{label_prefix}:{workspace_path}",
        "relative_path": workspace_path,
        "workspace_path": workspace_path,
        "absolute_path": str(resolved),
    }

"""Step handoff projection from role output."""

from typing import Protocol

from loopora.context_value_helpers import clean_text, gatekeeper_blockers, inspector_blockers, string_list
from loopora.run_artifacts import artifact_ref
from loopora.utils import structured_bool_is_true
from loopora.utils import coerced_non_negative_int


class StepHandoffContext(Protocol):
    layout: RunArtifactLayout
    iter_id: int
    step: dict
    step_order: int
    role: dict
    runtime_role: str
    output: dict


def build_step_handoff(result: StepHandoffContext) -> dict:
    archetype = str(result.role["archetype"])
    iter_id = coerced_non_negative_int(result.iter_id)
    step_order = coerced_non_negative_int(result.step_order)
    handoff = _handoff_core(archetype, result.output)
    artifact_refs = [
        artifact_ref(
            result.layout,
            result.layout.step_output_raw_path(iter_id, step_order, result.step["id"]),
            kind="step",
            label="output-raw",
        ),
        artifact_ref(
            result.layout,
            result.layout.step_output_normalized_path(iter_id, step_order, result.step["id"]),
            kind="step",
            label="output-normalized",
        ),
        artifact_ref(
            result.layout,
            result.layout.step_metadata_path(iter_id, step_order, result.step["id"]),
            kind="step",
            label="metadata",
        ),
    ]
    artifact_refs.extend(output_workspace_artifact_refs(result.layout, result.output))
    return {
        "source": {
            "iter": iter_id,
            "step_id": str(result.step["id"]),
            "step_order": step_order,
            "role_id": str(result.role["id"]),
            "role_name": str(result.role["name"]),
            "runtime_role": str(result.runtime_role),
            "archetype": archetype,
        },
        **handoff,
        "evidence_refs": [],
        "artifact_refs": artifact_refs,
    }


def _handoff_core(archetype: str, output: dict) -> dict:
    if archetype == "builder":
        return _builder_handoff(output)
    if archetype == "inspector":
        return _inspector_handoff(output)
    if archetype == "gatekeeper":
        return _gatekeeper_handoff(output)
    if archetype == "guide":
        return _guide_handoff(output)
    return _custom_handoff(output)


def _builder_handoff(output: dict) -> dict:
    summary = clean_text(output.get("summary") or output.get("attempted")) or "Builder completed its change pass."
    abandoned = clean_text(output.get("abandoned"))
    if abandoned:
        summary = f"{summary} Out-of-scope or unfinished note: {abandoned}"
    return {
        "status": "completed",
        "summary": summary,
        "blocking_items": [],
        "recommended_next_action": clean_text(output.get("assumption")) or "Validate the visible change with inspection.",
    }


def _inspector_handoff(output: dict) -> dict:
    blocking_items = inspector_blockers(output)
    return {
        "status": "blocked" if blocking_items else "completed",
        "summary": clean_text(output.get("tester_observations")) or "Inspector collected workspace evidence.",
        "blocking_items": blocking_items,
        "recommended_next_action": (
            "Address the failing checks with the strongest direct evidence."
            if blocking_items
            else "Pass the evidence bundle to GateKeeper for a verdict."
        ),
    }


def _gatekeeper_handoff(output: dict) -> dict:
    blocking_items = gatekeeper_blockers(output)
    status = "passed" if structured_bool_is_true(output.get("passed")) else "blocked"
    recommended_next_action = clean_text(output.get("feedback_to_builder") or output.get("feedback_to_generator"))
    if not recommended_next_action:
        recommended_next_action = (
            "No further role action is required; the GateKeeper verdict passed."
            if status == "passed"
            else "Continue only after the blocking issues are resolved."
        )
    return {
        "status": status,
        "summary": clean_text(output.get("decision_summary")) or "GateKeeper evaluated the current evidence.",
        "blocking_items": blocking_items,
        "recommended_next_action": recommended_next_action,
    }


def _guide_handoff(output: dict) -> dict:
    analysis = output.get("analysis") if isinstance(output.get("analysis"), dict) else {}
    blocking_items = []
    risk_note = clean_text(analysis.get("risk_note"))
    if risk_note:
        blocking_items.append(risk_note)
    return {
        "status": "advisory",
        "summary": clean_text(analysis.get("recommended_shift") or output.get("meta_note")) or "Guide proposed a direction shift.",
        "blocking_items": blocking_items,
        "recommended_next_action": (
            clean_text(output.get("seed_question") or analysis.get("recommended_shift"))
            or "Use the guidance as the next experiment seed."
        ),
    }


def _custom_handoff(output: dict) -> dict:
    blocking_items = [item for item in string_list(output.get("blocking_items")) if item]
    if not blocking_items:
        blocking_items = [item for item in string_list(output.get("risks")) if item]
    return {
        "status": clean_text(output.get("status")).lower() or "advisory",
        "summary": clean_text(output.get("summary") or output.get("handoff_note")) or "Custom role prepared a scoped handoff.",
        "blocking_items": blocking_items,
        "recommended_next_action": (
            clean_text(output.get("recommended_next_action"))
            or clean_text((string_list(output.get("recommendations")) or [""])[0] or output.get("handoff_note"))
            or "Use this handoff in a Builder or Inspector step."
        ),
    }
