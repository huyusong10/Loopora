from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.runtime_task_language import runtime_task_text
from loopora.structured_numbers import structured_non_negative_int


def summarize_evidence_coverage_projection(projection: Mapping[str, Any], *, coverage_path_available: bool = True) -> dict:
    coverage_path = str(projection.get("coverage_path") or "").strip() if coverage_path_available else ""
    targets = [dict(item) for item in list(projection.get("targets") or []) if isinstance(item, Mapping)]
    required_targets = [item for item in targets if coverage_target_is_required(item)]
    advisory_targets = [item for item in targets if not coverage_target_is_required(item)]
    return {
        "ledger_path": str(projection.get("ledger_path") or ""),
        "coverage_path": coverage_path,
        "status": str(projection.get("status") or "pending"),
        "summary": _mapping_or_empty(projection.get("summary")),
        "evidence_count": structured_non_negative_int(projection.get("evidence_count")),
        "check_count": structured_non_negative_int(projection.get("check_count")),
        "covered_check_count": structured_non_negative_int(projection.get("covered_check_count")),
        "missing_check_count": structured_non_negative_int(projection.get("missing_check_count")),
        "covered_check_ids": _projection_string_list(projection.get("covered_check_ids")),
        "missing_check_ids": _projection_string_list(projection.get("missing_check_ids")),
        "target_count": structured_non_negative_int(projection.get("target_count")),
        "covered_target_count": structured_non_negative_int(projection.get("covered_target_count")),
        "weak_target_count": structured_non_negative_int(projection.get("weak_target_count")),
        "missing_target_count": structured_non_negative_int(projection.get("missing_target_count")),
        "blocked_target_count": structured_non_negative_int(projection.get("blocked_target_count")),
        **_requirement_counts(required_targets, "required"),
        **_requirement_counts(advisory_targets, "advisory"),
        "top_gaps": _projection_mapping_list(projection.get("top_gaps"), limit=5),
        "evidence_kind_counts": _mapping_or_empty(projection.get("evidence_kind_counts")),
        "artifact_ref_count": structured_non_negative_int(projection.get("artifact_ref_count")),
        "residual_risk_count": structured_non_negative_int(projection.get("residual_risk_count")),
        "risk_signals": _projection_string_list(projection.get("risk_signals"), limit=5),
        "latest_gatekeeper": _mapping_or_empty(projection.get("latest_gatekeeper")),
    }


def _requirement_counts(targets: list[dict], requirement: str) -> dict[str, int]:
    return {
        f"{requirement}_target_count": len(targets),
        **{
            f"{status}_{requirement}_target_count": sum(1 for target in targets if str(target.get("status") or "missing").strip().lower() == status)
            for status in ("covered", "weak", "missing", "blocked")
        },
    }


def target_projection(row: Mapping[str, Any]) -> dict:
    return {
        "id": str(row.get("id") or ""),
        "kind": str(row.get("kind") or ""),
        "source_section": str(row.get("source_section") or ""),
        "source_id": str(row.get("source_id") or ""),
        "label": str(row.get("label") or ""),
        "text": str(row.get("text") or ""),
        "required": coverage_target_is_required(row),
        "status": str(row.get("status") or "missing"),
        "reason": str(row.get("reason") or ""),
        "evidence_refs": list(row.get("evidence_refs") or []),
        "artifact_refs": list(row.get("artifact_refs") or [])[:12],
    }


def top_coverage_gaps(target_rows: list[dict]) -> list[dict]:
    severity = {"blocked": 0, "missing": 1, "weak": 2}
    gaps = [row for row in target_rows if row.get("status") != "covered"]
    gaps.sort(key=lambda row: (0 if coverage_target_is_required(row) else 1, severity.get(str(row.get("status")), 9), str(row.get("id"))))
    return [
        {
            "target_id": row["id"],
            "kind": row["kind"],
            "source_section": row["source_section"],
            "status": row["status"],
            "required": coverage_target_is_required(row),
            "reason": row["reason"],
            "text": row["text"],
            "evidence_refs": row["evidence_refs"],
        }
        for row in gaps[:5]
    ]


def coverage_summary(status: str, top_gaps: list[dict], *, language: str = "en") -> dict:
    if status == "covered":
        reason = runtime_task_text(
            language,
            "Required and advisory coverage targets have supporting evidence.",
            "必需和建议覆盖目标都已有支持证据。",
        )
    elif status == "weak":
        reason = runtime_task_text(
            language,
            "Required targets are covered, but advisory evidence is incomplete.",
            "必需覆盖目标已经证明，但建议证据仍不完整。",
        )
    elif status == "partial":
        reason = runtime_task_text(
            language,
            "Required coverage targets still lack direct evidence.",
            "必需覆盖目标仍缺少直接证据。",
        )
    elif status == "blocked":
        reason = runtime_task_text(
            language,
            "GateKeeper or target evidence reported a blocker.",
            "GateKeeper 或目标证据报告了阻断项。",
        )
    elif status == "legacy":
        reason = runtime_task_text(
            language,
            "This run does not have a readable evidence ledger.",
            "这个 Run 没有可读取的证据账本。",
        )
    else:
        reason = runtime_task_text(
            language,
            "No evidence ledger entries are available yet.",
            "证据账本中还没有可用条目。",
        )
    return {
        "status": status,
        "reason": reason,
        "primary_gap": top_gaps[0] if top_gaps else {},
    }


def _mapping_or_empty(value: object) -> dict:
    return dict(value) if isinstance(value, Mapping) else {}


def _projection_string_list(value: object, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [item for item in value if isinstance(item, str)]
    return items[:limit] if limit is not None else items


def _projection_mapping_list(value: object, *, limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)][:limit]
