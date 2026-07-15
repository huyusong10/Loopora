from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.evidence_coverage import evidence_item_is_supporting_gatekeeper_ref
from loopora.utils import structured_bool_is_true
from loopora.utils import structured_non_negative_int


def _agent_native_compact_known_evidence_refs(
    known_evidence_ids: list[str],
    step_instruction_context: object,
) -> list[dict[str, Any]]:
    step_context = step_instruction_context if isinstance(step_instruction_context, dict) else {}
    evidence = step_context.get("evidence") if isinstance(step_context.get("evidence"), dict) else {}
    items_by_id = {
        str(item.get("id")): item
        for item in list(evidence.get("items") or [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    refs: list[dict[str, Any]] = []
    for evidence_id in known_evidence_ids:
        item = items_by_id.get(evidence_id)
        ref: dict[str, Any] = {"id": evidence_id}
        if isinstance(item, dict):
            ref.update(
                {
                    "step_id": str(item.get("step_id") or "").strip(),
                    "role_name": str(item.get("role_name") or "").strip(),
                    "archetype": str(item.get("archetype") or "").strip(),
                    "claim": str(item.get("claim") or "").strip(),
                    "result": str(item.get("result") or "").strip(),
                    "measured_evidence": bool(item.get("measured_evidence")),
                    "concrete_evidence_claim_count": structured_non_negative_int(
                        item.get("concrete_evidence_claim_count"),
                        default=0,
                    ),
                    "coverage_target_ids": _agent_native_evidence_coverage_target_ids(item),
                    "gatekeeper_support": _agent_native_gatekeeper_support_status(item),
                    "gatekeeper_support_reason": _agent_native_gatekeeper_support_reason(item),
                    "artifact_refs": _agent_native_compact_evidence_artifact_refs(item.get("artifact_refs")),
                }
            )
        refs.append(ref)
    return refs


def _agent_native_compact_evidence_artifact_refs(value: object, *, limit: int = 4) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for item in list(value or []):
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        kind = str(item.get("kind") or "").strip()
        path = str(item.get("workspace_path") or item.get("relative_path") or "").strip()
        if not path:
            continue
        if kind != "workspace" and not label.startswith(("proof-file:", "proof-artifact:", "artifact:")):
            continue
        compact = {"path": path}
        if label:
            compact["label"] = label
        refs.append(compact)
        if len(refs) >= limit:
            break
    return refs


def _agent_native_evidence_coverage_target_ids(item: dict[str, Any]) -> list[str]:
    target_ids: list[str] = []
    for coverage in list(item.get("coverage_results") or []):
        if not isinstance(coverage, dict):
            continue
        target_id = str(coverage.get("target_id") or "").strip()
        if target_id:
            target_ids.append(target_id)
    return list(dict.fromkeys(target_ids))


def _agent_native_gatekeeper_support_status(item: dict[str, Any]) -> str:
    return "supporting" if evidence_item_is_supporting_gatekeeper_ref(item) else "non_supporting"


def _agent_native_gatekeeper_support_reason(item: dict[str, Any]) -> str:
    archetype = str(item.get("archetype") or "").strip().lower()
    result = str(item.get("result") or "").strip().lower()
    reason = ""
    if evidence_item_is_supporting_gatekeeper_ref(item):
        if _agent_native_has_current_proof_artifact_ref(item.get("artifact_refs")):
            reason = "has a current proof-file or proof-artifact workspace ref"
        elif archetype in {"inspector", "custom"} and _agent_native_has_supporting_verify_ref(item.get("verifies")):
            reason = "review evidence verifies a passed check or coverage target"
        elif str(item.get("evidence_kind") or "").strip().lower() == "control":
            reason = "workflow control evidence is supportable"
        elif structured_bool_is_true(item.get("measured_evidence")):
            reason = "marked as measured evidence"
        else:
            reason = "matches supporting GateKeeper evidence rules"
    elif archetype == "gatekeeper":
        reason = "GateKeeper evidence cannot support another GateKeeper pass"
    elif result in {"blocked", "failed", "fail", "rejected", "error", "errored"}:
        reason = f"result is {result}"
    else:
        reason = "no proof artifact, measured evidence, control evidence, or supporting review verification"
    return reason


def _agent_native_has_current_proof_artifact_ref(value: object) -> bool:
    for ref in list(value or []):
        if not isinstance(ref, dict):
            continue
        label = str(ref.get("label") or "").strip().lower()
        if not label.startswith(("proof-file:", "proof-artifact:")):
            continue
        absolute_path = str(ref.get("absolute_path") or "").strip()
        if not absolute_path:
            continue
        try:
            if Path(absolute_path).exists():
                return True
        except OSError:
            continue
    return False


def _agent_native_has_supporting_verify_ref(value: object) -> bool:
    supporting_results = {
        "passed",
        "pass",
        "ok",
        "success",
        "succeeded",
        "completed",
        "covered",
        "satisfied",
        "guarded",
        "verified",
        "proven",
    }
    for raw_ref in list(value or []):
        text = str(raw_ref or "").strip()
        if text.startswith("target:"):
            parts = text.split(":", 2)
            if len(parts) == 3 and parts[2].strip().lower() in supporting_results:
                return True
        if text.startswith(("check_results:", "dynamic_checks:")):
            parts = text.split(":", 2)
            if len(parts) == 3 and parts[2].strip().lower() in supporting_results:
                return True
    return False
