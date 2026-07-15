from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.evidence_coverage_summary import (
    coverage_summary as _coverage_summary,
    summarize_evidence_coverage_projection as summarize_evidence_coverage_projection,
    target_projection as _target_projection,
    top_coverage_gaps as _top_coverage_gaps,
)
from loopora.evidence_coverage_targets import (
    build_coverage_targets,
    parse_target_verify_ref,
    with_coverage_targets as with_coverage_targets,
)
from loopora.residual_risk_support import residual_risk_is_meaningful
from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from loopora.utils import structured_non_negative_int
from loopora.utils import read_json, utc_now, write_json








from loopora.utils import structured_bool_is_true



from pathlib import Path



NON_SUPPORTING_EVIDENCE_RESULTS = {"blocked", "failed", "fail", "rejected", "error", "errored"}

SUPPORTING_EVIDENCE_RESULTS = {"passed", "pass", "ok", "success", "succeeded", "completed", "covered", "satisfied", "guarded", "verified", "proven"}

SUPPORTING_REVIEW_ARCHETYPES = {"inspector", "custom"}

def evidence_item_is_supporting_gatekeeper_ref(item: Mapping[str, Any]) -> bool:
    if not isinstance(item, Mapping):
        return False
    archetype = str(item.get("archetype") or "").strip().lower()
    result = str(item.get("result") or "").strip().lower()
    if archetype == "gatekeeper" or result in NON_SUPPORTING_EVIDENCE_RESULTS:
        return False
    if archetype in SUPPORTING_REVIEW_ARCHETYPES and _has_supporting_review_verify_ref(item.get("verifies")):
        return True
    if str(item.get("evidence_kind") or "").strip().lower() == "control":
        return True
    if structured_bool_is_true(item.get("measured_evidence")):
        return True
    return _has_proof_artifact_ref(item.get("artifact_refs"))

def evidence_item_is_non_supporting_gatekeeper_ref(item: Mapping[str, Any]) -> bool:
    return isinstance(item, Mapping) and not evidence_item_is_supporting_gatekeeper_ref(item)

def _has_proof_artifact_ref(value: object) -> bool:
    for ref in list(value or []):
        if not isinstance(ref, Mapping):
            continue
        label = str(ref.get("label") or "").strip().lower()
        if label.startswith(("proof-file:", "proof-artifact:")) and _artifact_ref_currently_exists(ref):
            return True
    return False

def _has_supporting_review_verify_ref(value: object) -> bool:
    return any(_verify_ref_has_supporting_status(ref) for ref in list(value or []))

def _verify_ref_has_supporting_status(value: object) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.startswith("target:"):
        parts = text.split(":", 2)
        return len(parts) == 3 and parts[2].strip().lower() in SUPPORTING_EVIDENCE_RESULTS
    if text.startswith(("check_results:", "dynamic_checks:")):
        parts = text.split(":", 2)
        return len(parts) == 3 and parts[2].strip().lower() in SUPPORTING_EVIDENCE_RESULTS
    return False

def _artifact_ref_currently_exists(ref: Mapping[str, Any]) -> bool:
    absolute_path = str(ref.get("absolute_path") or "").strip()
    if not absolute_path:
        return False
    try:
        return Path(absolute_path).exists()
    except OSError:
        return False

def latest_gatekeeper_projection(
    item: Mapping[str, Any],
    *,
    item_id: str,
    risk: str,
    evidence_items_by_id: Mapping[str, Mapping[str, Any]],
) -> dict:
    if str(item.get("archetype") or "").strip().lower() != "gatekeeper":
        return {}
    gatekeeper_refs = _gatekeeper_evidence_refs(item)
    return {
        "id": item_id,
        "result": str(item.get("result") or "").strip(),
        "evidence_refs": gatekeeper_refs,
        "supporting_evidence_refs": _supporting_gatekeeper_refs(gatekeeper_refs, evidence_items_by_id),
        "non_supporting_evidence_refs": _non_supporting_gatekeeper_refs(gatekeeper_refs, evidence_items_by_id, current_id=item_id),
        "self_measured_evidence": gatekeeper_has_self_measured_evidence(item, item_id=item_id, evidence_refs=gatekeeper_refs),
        "self_evidence_claim_count": structured_non_negative_int(item.get("concrete_evidence_claim_count")),
        "residual_risk": risk,
    }

def apply_gatekeeper_target(target_state: dict[str, dict], latest_gatekeeper: Mapping[str, Any]) -> None:
    row = target_state.get("gatekeeper.finish")
    if not row or not latest_gatekeeper:
        return
    result = str(latest_gatekeeper.get("result") or "").strip().lower()
    gatekeeper_id = str(latest_gatekeeper.get("id") or "").strip()
    evidence_refs = [str(item).strip() for item in list(latest_gatekeeper.get("evidence_refs") or []) if str(item).strip()]
    supporting_refs = [str(item).strip() for item in list(latest_gatekeeper.get("supporting_evidence_refs") or []) if str(item).strip()]
    non_supporting_refs = [str(item).strip() for item in list(latest_gatekeeper.get("non_supporting_evidence_refs") or []) if str(item).strip()]
    has_self_measured_evidence = structured_bool_is_true(latest_gatekeeper.get("self_measured_evidence"))
    if result == "passed" and supporting_refs:
        row["status"] = "covered"
        row["reason"] = "GateKeeper passed with supporting upstream evidence refs."
        row["evidence_refs"] = list(dict.fromkeys([*supporting_refs, gatekeeper_id]))
    elif result == "passed" and has_self_measured_evidence:
        row["status"] = "covered"
        row["reason"] = "GateKeeper passed with measured self evidence and concrete evidence claims."
        row["evidence_refs"] = [gatekeeper_id] if gatekeeper_id else []
    elif result == "passed" and evidence_refs and non_supporting_refs and not supporting_refs:
        row["status"] = "blocked"
        row["reason"] = "GateKeeper pass cited only non-supporting upstream evidence refs."
        row["evidence_refs"] = list(dict.fromkeys([*non_supporting_refs, gatekeeper_id]))
    elif result in {"blocked", "failed", "rejected"}:
        row["status"] = "blocked"
        row["reason"] = "GateKeeper blocked the run."
        row["evidence_refs"] = [gatekeeper_id] if gatekeeper_id else []

def gatekeeper_has_self_measured_evidence(item: Mapping[str, Any], *, item_id: str, evidence_refs: list[str]) -> bool:
    if not item_id or item_id not in set(evidence_refs):
        return False
    if str(item.get("result") or "").strip().lower() != "passed":
        return False
    return structured_bool_is_true(item.get("measured_evidence")) and structured_non_negative_int(item.get("concrete_evidence_claim_count")) > 0

def _gatekeeper_evidence_refs(item: Mapping[str, Any]) -> list[str]:
    refs = [
        str(ref).split(":", 1)[1].strip()
        for ref in list(item.get("verifies") or [])
        if str(ref).startswith("evidence:") and str(ref).split(":", 1)[1].strip()
    ]
    if refs:
        return list(dict.fromkeys(refs))
    return list(
        dict.fromkeys(str(ref).strip() for ref in list(item.get("related_evidence_ids") or []) if str(ref).strip())
    )

def _supporting_gatekeeper_refs(evidence_refs: list[str], evidence_items_by_id: Mapping[str, Mapping[str, Any]]) -> list[str]:
    refs: list[str] = []
    for ref in evidence_refs:
        item = evidence_items_by_id.get(str(ref).strip())
        if not item:
            continue
        if evidence_item_is_supporting_gatekeeper_ref(item):
            refs.append(str(ref).strip())
    return list(dict.fromkeys(refs))

def _non_supporting_gatekeeper_refs(
    evidence_refs: list[str],
    evidence_items_by_id: Mapping[str, Mapping[str, Any]],
    *,
    current_id: str,
) -> list[str]:
    refs: list[str] = []
    for ref in evidence_refs:
        if str(ref).strip() == str(current_id or "").strip():
            continue
        item = evidence_items_by_id.get(str(ref).strip())
        if not item:
            continue
        if evidence_item_is_non_supporting_gatekeeper_ref(item):
            refs.append(str(ref).strip())
    return list(dict.fromkeys(refs))

_apply_gatekeeper_target = apply_gatekeeper_target
_latest_gatekeeper_projection = latest_gatekeeper_projection
_gatekeeper_has_self_measured_evidence = gatekeeper_has_self_measured_evidence

POSITIVE_COVERAGE_STATUSES = {
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

WEAK_COVERAGE_STATUSES = {"partial", "weak", "skipped", "unknown", "inconclusive"}

MISSING_COVERAGE_STATUSES = {"missing"}

NEGATIVE_COVERAGE_STATUSES = {"failed", "fail", "error", "errored", "blocked", "rejected"}

def apply_target_evidence(
    row: dict,
    *,
    status: str,
    item: Mapping[str, Any],
    evidence_items_by_id: Mapping[str, Mapping[str, Any]],
    target_evidence_refs: list[str] | None,
) -> None:
    normalized = str(status or "unknown").strip().lower()
    evidence_id = str(item.get("id") or "").strip()
    supporting_refs = _target_supporting_refs(
        item=item,
        evidence_items_by_id=evidence_items_by_id,
        target_evidence_refs=target_evidence_refs,
    )
    _apply_target_status(row, normalized=normalized, supporting_refs=supporting_refs)
    evidence_refs = _target_row_evidence_refs(normalized=normalized, evidence_id=evidence_id, supporting_refs=supporting_refs)
    if evidence_refs:
        row["evidence_refs"] = list(dict.fromkeys([*list(row.get("evidence_refs") or []), *evidence_refs]))
    artifact_refs = _target_artifact_refs(item=item, supporting_refs=supporting_refs, evidence_items_by_id=evidence_items_by_id)
    if artifact_refs:
        row["artifact_refs"] = list(row.get("artifact_refs") or []) + artifact_refs[:8]

def coverage_result_rows(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    rows: list[dict] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        target_id = str(item.get("target_id") or "").strip()
        if not target_id or ":" in target_id:
            continue
        rows.append(
            {
                "target_id": target_id,
                "status": str(item.get("status") or "unknown").strip() or "unknown",
                "evidence_refs": _string_list(item.get("evidence_refs")),
            }
        )
    return rows

def _apply_target_status(row: dict, *, normalized: str, supporting_refs: list[str]) -> None:
    if normalized in NEGATIVE_COVERAGE_STATUSES:
        row["status"] = "blocked"
        row["reason"] = "Evidence reported this coverage target as blocked or failed."
    elif normalized in MISSING_COVERAGE_STATUSES:
        if row.get("status") not in {"blocked", "covered", "weak"}:
            row["status"] = "missing"
            row["reason"] = "Evidence reported this coverage target is still missing."
    elif normalized in POSITIVE_COVERAGE_STATUSES:
        if supporting_refs:
            if row.get("status") != "covered":
                row["evidence_refs"] = []
                row["artifact_refs"] = []
            row["status"] = "covered"
            row["reason"] = "Supporting evidence verified this coverage target."
        elif row.get("status") not in {"blocked", "covered"}:
            row["status"] = "weak"
            row["reason"] = "Coverage was reported as positive without supporting evidence."
    elif normalized in WEAK_COVERAGE_STATUSES and row.get("status") not in {"blocked", "covered"}:
        row["status"] = "weak"
        row["reason"] = "Evidence for this coverage target is present but weak or inconclusive."

def _target_row_evidence_refs(*, normalized: str, evidence_id: str, supporting_refs: list[str]) -> list[str]:
    if normalized in NEGATIVE_COVERAGE_STATUSES:
        return list(dict.fromkeys([*([evidence_id] if evidence_id else []), *supporting_refs]))
    return supporting_refs or ([evidence_id] if evidence_id else [])

def _target_supporting_refs(
    *,
    item: Mapping[str, Any],
    evidence_items_by_id: Mapping[str, Mapping[str, Any]],
    target_evidence_refs: list[str] | None,
) -> list[str]:
    refs: list[str] = []
    evidence_id = str(item.get("id") or "").strip()
    if evidence_id and evidence_item_is_supporting_gatekeeper_ref(item):
        refs.append(evidence_id)
    if evidence_id and _gatekeeper_has_self_measured_evidence(item, item_id=evidence_id, evidence_refs=[evidence_id]):
        refs.append(evidence_id)
    related_ids = target_evidence_refs if target_evidence_refs is not None else _string_list(item.get("related_evidence_ids"))
    for related_id in related_ids:
        related_item = evidence_items_by_id.get(related_id)
        if related_item and evidence_item_is_supporting_gatekeeper_ref(related_item):
            refs.append(related_id)
    return list(dict.fromkeys(refs))

def _target_artifact_refs(
    *,
    item: Mapping[str, Any],
    supporting_refs: list[str],
    evidence_items_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict]:
    refs: list[dict] = []
    if not supporting_refs:
        return list(item.get("artifact_refs") or []) if isinstance(item.get("artifact_refs"), list) else []
    for evidence_id in supporting_refs:
        source_item = evidence_items_by_id.get(evidence_id)
        if not source_item:
            continue
        artifact_refs = source_item.get("artifact_refs") if isinstance(source_item.get("artifact_refs"), list) else []
        refs.extend(ref for ref in artifact_refs if isinstance(ref, dict))
    return refs

def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

_apply_target_evidence = apply_target_evidence
_coverage_result_rows = coverage_result_rows


def write_evidence_coverage_projection(layout: RunArtifactLayout) -> dict:
    projection = build_evidence_coverage_projection(layout)
    write_json(layout.evidence_coverage_path, projection)
    return projection


def load_or_build_evidence_coverage_projection(layout: RunArtifactLayout) -> dict:
    if layout.evidence_coverage_path.exists():
        try:
            payload = read_json(layout.evidence_coverage_path)
        except (OSError, UnicodeError, ValueError):
            payload = {}
        if isinstance(payload, dict) and payload.get("schema_version") == 1:
            return payload
    return build_evidence_coverage_projection(layout)


def build_evidence_coverage_projection(layout: RunArtifactLayout) -> dict:
    compiled_spec = _safe_read_json_artifact(layout.contract_compiled_spec_path)
    run_contract = _safe_read_json_artifact(layout.run_contract_path)
    completion_mode = str(run_contract.get("completion_mode") or "gatekeeper").strip().lower() or "gatekeeper"
    targets = build_coverage_targets(compiled_spec, completion_mode=completion_mode)
    ledger_exists = layout.evidence_ledger_path.exists()
    evidence_items = read_jsonl(layout.evidence_ledger_path)
    target_state = _initial_target_state(targets)
    evidence_kind_counts: Counter[str] = Counter()
    artifact_ref_count = 0
    risk_signals: list[str] = []
    latest_gatekeeper: dict = {}
    evidence_items_by_id: dict[str, Mapping[str, Any]] = {}

    if not ledger_exists:
        status = "legacy"
    elif not evidence_items:
        status = "pending"
    else:
        for item in evidence_items:
            item_projection = _collect_coverage_evidence_item(
                item,
                target_state=target_state,
                evidence_items_by_id=evidence_items_by_id,
                evidence_kind_counts=evidence_kind_counts,
            )
            if not item_projection:
                continue
            artifact_ref_count += structured_non_negative_int(item_projection.get("artifact_ref_count"))
            risk = str(item_projection.get("risk") or "")
            if risk:
                risk_signals.append(risk)
            if item_projection.get("latest_gatekeeper"):
                latest_gatekeeper = dict(item_projection["latest_gatekeeper"])

        _apply_gatekeeper_target(target_state, latest_gatekeeper)
        status = _overall_coverage_status(target_state)

    target_rows = [_target_projection(row) for row in target_state.values()]
    top_gaps = _top_coverage_gaps(target_rows)
    covered_check_ids = [row["source_id"] for row in target_rows if row["kind"] == "done_when" and row["status"] == "covered"]
    missing_check_ids = [row["source_id"] for row in target_rows if row["kind"] == "done_when" and row["status"] != "covered"]
    summary = _coverage_summary(status, top_gaps)
    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "ledger_path": layout.relative(layout.evidence_ledger_path),
        "coverage_path": layout.relative(layout.evidence_coverage_path),
        "status": status,
        "summary": summary,
        "target_count": len(target_rows),
        "covered_target_count": sum(1 for row in target_rows if row["status"] == "covered"),
        "weak_target_count": sum(1 for row in target_rows if row["status"] == "weak"),
        "missing_target_count": sum(1 for row in target_rows if row["status"] == "missing"),
        "blocked_target_count": sum(1 for row in target_rows if row["status"] == "blocked"),
        "check_count": len([row for row in target_rows if row["kind"] == "done_when"]),
        "covered_check_count": len(covered_check_ids),
        "missing_check_count": len(missing_check_ids),
        "covered_check_ids": covered_check_ids,
        "missing_check_ids": missing_check_ids,
        "evidence_count": len(evidence_items),
        "evidence_kind_counts": dict(evidence_kind_counts),
        "artifact_ref_count": artifact_ref_count,
        "residual_risk_count": len(risk_signals),
        "risk_signals": list(dict.fromkeys(risk_signals))[:5],
        "latest_gatekeeper": latest_gatekeeper,
        "top_gaps": top_gaps,
        "targets": target_rows,
    }


def _safe_read_json_artifact(path) -> dict:
    try:
        payload = read_json(path)
    except (OSError, UnicodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _initial_target_state(targets: list[dict]) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for target in targets:
        target_id = str(target.get("id") or "").strip()
        if not target_id or target_id in rows:
            continue
        rows[target_id] = {
            **target,
            "status": "missing",
            "reason": "No evidence has verified this coverage target.",
            "evidence_refs": [],
            "artifact_refs": [],
        }
    return rows


def _collect_coverage_evidence_item(
    item: object,
    *,
    target_state: dict[str, dict],
    evidence_items_by_id: dict[str, Mapping[str, Any]],
    evidence_kind_counts: Counter[str],
) -> dict:
    if not isinstance(item, Mapping):
        return {}
    item_id = str(item.get("id") or "").strip()
    if item_id:
        evidence_items_by_id[item_id] = item
    kind = str(item.get("evidence_kind") or "observation").strip() or "observation"
    evidence_kind_counts[kind] += 1
    artifact_refs = item.get("artifact_refs") if isinstance(item.get("artifact_refs"), list) else []
    risk = _clean_residual_risk_text(item.get("residual_risk"))

    coverage_result_target_ids: set[str] = set()
    for coverage_result in _coverage_result_rows(item.get("coverage_results")):
        target_id = coverage_result["target_id"]
        if target_id not in target_state:
            continue
        coverage_result_target_ids.add(target_id)
        _apply_target_evidence(
            target_state[target_id],
            status=coverage_result["status"],
            item=item,
            evidence_items_by_id=evidence_items_by_id,
            target_evidence_refs=coverage_result["evidence_refs"],
        )

    for verify_ref in list(item.get("verifies") or []):
        parsed = parse_target_verify_ref(verify_ref)
        if not parsed:
            continue
        target_id, target_status = parsed
        if target_id in coverage_result_target_ids:
            continue
        if target_id in target_state:
            _apply_target_evidence(
                target_state[target_id],
                status=target_status,
                item=item,
                evidence_items_by_id=evidence_items_by_id,
                target_evidence_refs=None,
            )

    return {
        "artifact_ref_count": len(artifact_refs),
        "risk": risk if _is_meaningful_residual_risk(risk) else "",
        "latest_gatekeeper": _latest_gatekeeper_projection(item, item_id=item_id, risk=risk, evidence_items_by_id=evidence_items_by_id),
    }


def _overall_coverage_status(target_state: Mapping[str, dict]) -> str:
    rows = list(target_state.values())
    if any(row.get("status") == "blocked" for row in rows):
        return "blocked"
    if any(coverage_target_is_required(row) and row.get("status") != "covered" for row in rows):
        return "partial"
    if any((not coverage_target_is_required(row)) and row.get("status") in {"missing", "weak", "blocked"} for row in rows):
        return "weak"
    return "covered"


def _clean_text(value: object, *, max_length: int | None = 500) -> str:
    text = " ".join(str(value or "").split()).strip()
    if max_length is not None and len(text) > max_length:
        return text[: max_length - 1].rstrip() + "…"
    return text


def _clean_residual_risk_text(value: object) -> str:
    return _clean_text(value, max_length=None)


def _is_meaningful_residual_risk(value: object) -> bool:
    text = _clean_residual_risk_text(value)
    return residual_risk_is_meaningful(text)
