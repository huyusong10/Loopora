from __future__ import annotations

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.structured_booleans import structured_bool_is_true


def clean_text(value: object) -> str:
    return str(value or "").strip()


def string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def unique_string_list(value: object) -> list[str]:
    return list(dict.fromkeys(string_list(value)))


def inspector_blockers(output: dict) -> list[str]:
    blockers = []
    failed_items = output.get("failed_items")
    if isinstance(failed_items, list):
        blockers.extend(str(item.get("title") or item.get("id") or "").strip() for item in failed_items if item)
    for bucket_name in ("check_results", "dynamic_checks"):
        for item in output.get(bucket_name, []) or []:
            if str(item.get("status") or "").strip() == "passed":
                continue
            blocker = str(item.get("title") or item.get("id") or "").strip()
            if blocker:
                blockers.append(blocker)
    return list(dict.fromkeys(item for item in blockers if item))


def gatekeeper_blockers(output: dict) -> list[str]:
    blockers = []
    blockers.extend(string_list(output.get("blocking_issues")))
    blockers.extend(string_list(output.get("hard_constraint_violations")))
    blockers.extend(string_list(output.get("failed_check_ids")))
    priority_failures = output.get("priority_failures")
    if isinstance(priority_failures, list):
        blockers.extend(str(item.get("summary") or item.get("error_code") or "").strip() for item in priority_failures if isinstance(item, dict))
    return list(dict.fromkeys(item for item in blockers if item))


def evidence_coverage_results(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    results: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        if not target_id or ":" in target_id:
            continue
        results.append(
            {
                "target_id": target_id,
                "status": clean_text(item.get("status")) or "unknown",
                "evidence_refs": unique_string_list(item.get("evidence_refs"))[:20],
                "note": clean_text(item.get("note"))[:400],
            }
        )
    return results[:20]


def normalize_coverage_gap_rows(value: object, *, limit: int = 5) -> list[dict]:
    if not isinstance(value, list):
        return []
    rows: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        target_id = str(item.get("target_id") or "").strip()
        if not target_id:
            continue
        rows.append(
            {
                "target_id": target_id,
                "kind": str(item.get("kind") or "").strip(),
                "source_section": str(item.get("source_section") or "").strip(),
                "status": str(item.get("status") or "missing").strip() or "missing",
                "required": structured_bool_is_true(item.get("required")),
                "reason": str(item.get("reason") or "").strip(),
                "text": str(item.get("text") or "").strip(),
                "evidence_refs": string_list(item.get("evidence_refs"))[:8],
            }
        )
    return rows[:limit]


def normalize_manifest_claim_coverage_targets(value: object) -> list[dict]:
    rows: list[dict] = []
    for item in list(value or []):
        if isinstance(item, dict):
            target_id = str(item.get("id") or item.get("target_id") or "").strip()
            if not target_id:
                continue
            rows.append(
                {
                    "id": target_id,
                    "kind": str(item.get("kind") or "").strip(),
                    "label": str(item.get("label") or target_id).strip(),
                    "reported_status": str(item.get("reported_status") or item.get("status") or "unknown").strip(),
                    "coverage_status": str(item.get("coverage_status") or "unknown").strip(),
                    "required": coverage_target_is_required(item, target_id=target_id),
                    "evidence_refs": string_list(item.get("evidence_refs"))[:8],
                }
            )
            continue
        target_id = str(item or "").strip()
        if target_id:
            rows.append(
                {
                    "id": target_id,
                    "kind": "",
                    "label": target_id,
                    "reported_status": "unknown",
                    "coverage_status": "unknown",
                    "required": coverage_target_is_required({}, target_id=target_id),
                    "evidence_refs": [],
                }
            )
    return rows[:20]
