from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.evidence_coverage_gatekeeper import (
    apply_gatekeeper_target as _apply_gatekeeper_target,
    latest_gatekeeper_projection as _latest_gatekeeper_projection,
)
from loopora.evidence_coverage_summary import (
    coverage_summary as _coverage_summary,
    summarize_evidence_coverage_projection as summarize_evidence_coverage_projection,
    target_projection as _target_projection,
    top_coverage_gaps as _top_coverage_gaps,
)
from loopora.evidence_coverage_target_application import apply_target_evidence as _apply_target_evidence
from loopora.evidence_coverage_target_application import coverage_result_rows as _coverage_result_rows
from loopora.evidence_coverage_targets import (
    build_coverage_targets,
    parse_target_verify_ref,
    with_coverage_targets as with_coverage_targets,
)
from loopora.residual_risk_support import residual_risk_is_meaningful
from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from loopora.runtime_task_language import runtime_task_language, runtime_task_text
from loopora.structured_numbers import structured_non_negative_int
from loopora.utils import read_json, utc_now, write_json


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
    task_language = runtime_task_language(compiled_spec)
    targets = build_coverage_targets(compiled_spec, completion_mode=completion_mode)
    ledger_exists = layout.evidence_ledger_path.exists()
    evidence_items = read_jsonl(layout.evidence_ledger_path)
    target_state = _initial_target_state(targets, language=task_language)
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

        _apply_gatekeeper_target(target_state, latest_gatekeeper, language=task_language)
        status = _overall_coverage_status(target_state)

    target_rows = [_target_projection(row) for row in target_state.values()]
    top_gaps = _top_coverage_gaps(target_rows)
    covered_check_ids = [row["source_id"] for row in target_rows if row["kind"] == "done_when" and row["status"] == "covered"]
    missing_check_ids = [row["source_id"] for row in target_rows if row["kind"] == "done_when" and row["status"] != "covered"]
    summary = _coverage_summary(status, top_gaps, language=task_language)
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


def _initial_target_state(targets: list[dict], *, language: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for target in targets:
        target_id = str(target.get("id") or "").strip()
        if not target_id or target_id in rows:
            continue
        rows[target_id] = {
            **target,
            "status": "missing",
            "reason": runtime_task_text(
                language,
                "No evidence has verified this coverage target.",
                "还没有证据验证这个覆盖目标。",
            ),
            "_display_language": language,
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
