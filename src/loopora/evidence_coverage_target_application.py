from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.evidence_coverage_gatekeeper import (
    gatekeeper_has_self_measured_evidence as _gatekeeper_has_self_measured_evidence,
)
from loopora.evidence_support import evidence_item_is_supporting_gatekeeper_ref
from loopora.runtime_task_language import runtime_task_text

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
    _apply_target_status(
        row,
        normalized=normalized,
        supporting_refs=supporting_refs,
        language=str(row.get("_display_language") or "en"),
    )
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


def _apply_target_status(row: dict, *, normalized: str, supporting_refs: list[str], language: str) -> None:
    if normalized in NEGATIVE_COVERAGE_STATUSES:
        row["status"] = "blocked"
        row["reason"] = runtime_task_text(
            language,
            "Evidence reported this coverage target as blocked or failed.",
            "证据报告这个覆盖目标已阻断或失败。",
        )
    elif normalized in MISSING_COVERAGE_STATUSES:
        if row.get("status") not in {"blocked", "covered", "weak"}:
            row["status"] = "missing"
            row["reason"] = runtime_task_text(
                language,
                "Evidence reported this coverage target is still missing.",
                "证据报告这个覆盖目标仍然缺失。",
            )
    elif normalized in POSITIVE_COVERAGE_STATUSES:
        if supporting_refs:
            if row.get("status") != "covered":
                row["evidence_refs"] = []
                row["artifact_refs"] = []
            row["status"] = "covered"
            row["reason"] = runtime_task_text(
                language,
                "Supporting evidence verified this coverage target.",
                "支持结论的证据已经验证这个覆盖目标。",
            )
        elif row.get("status") not in {"blocked", "covered"}:
            row["status"] = "weak"
            row["reason"] = runtime_task_text(
                language,
                "Coverage was reported as positive without supporting evidence.",
                "覆盖结果被报告为正向，但没有支持结论的证据。",
            )
    elif normalized in WEAK_COVERAGE_STATUSES and row.get("status") not in {"blocked", "covered"}:
        row["status"] = "weak"
        row["reason"] = runtime_task_text(
            language,
            "Evidence for this coverage target is present but weak or inconclusive.",
            "这个覆盖目标已有证据，但证据偏弱或结论不明确。",
        )


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
