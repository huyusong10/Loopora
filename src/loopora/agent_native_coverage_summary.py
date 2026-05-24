from __future__ import annotations

from loopora.cli_summary_helpers import clip_inline, non_bool_int


def required_coverage_summary(required_coverage: object) -> str:
    if not isinstance(required_coverage, dict):
        return ""
    status = str(required_coverage.get("status") or "pending").strip()
    status_label = "partial evidence" if status == "partial" else status
    covered = non_bool_int(required_coverage.get("covered_check_count"))
    missing = non_bool_int(required_coverage.get("missing_check_count"))
    target_count = non_bool_int(required_coverage.get("target_count"))
    covered_targets = non_bool_int(required_coverage.get("covered_target_count"))
    weak_targets = non_bool_int(required_coverage.get("weak_target_count"))
    missing_targets = non_bool_int(required_coverage.get("missing_target_count"))
    blocked_targets = non_bool_int(required_coverage.get("blocked_target_count"))
    bits = []
    if covered is not None or missing is not None:
        bits.append(f"required checks {covered or 0} covered / {missing or 0} missing")
    if target_count:
        target_bits = [f"{covered_targets or 0}/{target_count} targets covered"]
        if weak_targets:
            target_bits.append(f"{weak_targets} weak")
        if missing_targets:
            target_bits.append(f"{missing_targets} missing")
        if blocked_targets:
            target_bits.append(f"{blocked_targets} blocked")
        bits.append(" / ".join(target_bits))
    if not bits:
        return status_label
    return f"{status_label}; {', '.join(bits)}"


def coverage_classification_note(next_step: dict) -> str:
    known_count = non_bool_int(next_step.get("known_evidence_count"))
    if known_count is None and isinstance(next_step.get("known_evidence_ids"), list):
        known_count = len([item for item in next_step["known_evidence_ids"] if str(item).strip()])
    if not known_count:
        return ""
    coverage = next_step.get("required_coverage") if isinstance(next_step.get("required_coverage"), dict) else {}
    target_count = non_bool_int(coverage.get("target_count"))
    if not target_count:
        return ""
    covered_targets = non_bool_int(coverage.get("covered_target_count")) or 0
    weak_targets = non_bool_int(coverage.get("weak_target_count")) or 0
    blocked_targets = non_bool_int(coverage.get("blocked_target_count")) or 0
    if covered_targets or weak_targets or blocked_targets:
        if _coverage_gaps_only_gatekeeper_finish(coverage):
            return ""
        latest_unclassified = _latest_unclassified_supporting_evidence_id(next_step.get("known_evidence_refs"))
        if latest_unclassified:
            return (
                f"{latest_unclassified} is citable, but coverage still reflects earlier classifications until "
                "a review role returns coverage_results for that evidence"
            )
        return ""
    return (
        "known evidence is citable, but coverage remains unverified until a review role returns "
        "coverage_results with exact target IDs"
    )


def coverage_gap_summaries(gaps: object, *, limit: int) -> list[dict[str, object]]:
    if not isinstance(gaps, list):
        return []
    summaries: list[dict[str, object]] = []
    for gap in [item for item in gaps if isinstance(item, dict)][:limit]:
        summary: dict[str, object] = {}
        _set_summary_text(summary, "target_id", gap.get("target_id") or gap.get("id"))
        _set_summary_text(summary, "status", gap.get("status"))
        _set_summary_text(summary, "source_section", gap.get("source_section"))
        _set_summary_text(summary, "reason", clip_inline(str(gap.get("reason") or ""), 180))
        _set_summary_text(summary, "text", clip_inline(str(gap.get("text") or ""), 180))
        evidence_refs = evidence_scope_items(gap.get("evidence_refs"))
        if evidence_refs:
            summary["evidence_refs"] = evidence_refs[:5]
        if summary:
            summaries.append(summary)
    return summaries


def evidence_scope_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _coverage_gaps_only_gatekeeper_finish(coverage: dict) -> bool:
    if (non_bool_int(coverage.get("missing_check_count")) or 0) != 0:
        return False
    gaps = [gap for gap in list(coverage.get("top_gaps") or []) if isinstance(gap, dict)]
    if not gaps:
        return False
    return all(str(gap.get("target_id") or gap.get("id") or "").strip() == "gatekeeper.finish" for gap in gaps)


def _latest_unclassified_supporting_evidence_id(value: object) -> str:
    if not isinstance(value, list):
        return ""
    for item in reversed(value):
        if not isinstance(item, dict):
            continue
        evidence_id = str(item.get("id") or "").strip()
        if not evidence_id:
            continue
        support = str(item.get("gatekeeper_support") or "").strip().lower()
        if support and support != "supporting":
            continue
        if evidence_scope_items(item.get("coverage_target_ids")):
            continue
        if str(item.get("archetype") or "").strip().lower() == "gatekeeper":
            continue
        return evidence_id
    return ""


def _set_summary_text(summary: dict[str, object], key: str, value: object) -> None:
    text = str(value or "").strip()
    if text:
        summary[key] = text
