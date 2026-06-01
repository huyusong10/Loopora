from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.run_takeaway_common import (
    _int_value,
    _string_list,
    _string_value,
    clean_takeaway_text,
    display_iter,
    display_role_name,
    normalize_takeaway_status,
    safe_read_json_file,
)
from loopora.run_takeaway_iteration_verdicts import (
    active_takeaway_run_status,
    terminal_task_verdict_status_for_iteration,
    terminal_task_verdict_summary_for_iteration,
)
from loopora.structured_numbers import structured_non_negative_int


def build_role_takeaway_from_handoff(handoff: Mapping[str, object], *, composite_score: object = None) -> dict:
    source = handoff.get("source") if isinstance(handoff.get("source"), Mapping) else {}
    iter_id = _int_value(source.get("iter"), default=0) or 0
    step_order = _int_value(source.get("step_order"), default=0) or 0
    role_name = display_role_name(
        source.get("role_name"),
        archetype=source.get("archetype"),
        runtime_role=source.get("runtime_role"),
    )
    blocking_items = [clean_takeaway_text(item, max_length=520) for item in _string_list(handoff.get("blocking_items"))]
    next_action = clean_takeaway_text(handoff.get("recommended_next_action"), max_length=520)
    step_id = _string_value(source.get("step_id"))
    return {
        "id": f"iter-{iter_id}-{step_id or role_name}",
        "step_id": step_id,
        "step_order": step_order,
        "role_name": role_name,
        "archetype": _string_value(source.get("archetype")).lower(),
        "status": normalize_takeaway_status(handoff.get("status")),
        "summary": clean_takeaway_text(handoff.get("summary"), max_length=1200),
        "blocking_item": " · ".join(blocking_items),
        "next_action": next_action,
        "evidence_refs": _string_list(handoff.get("evidence_refs")),
        "composite_score": composite_score,
    }


def build_structured_iteration_takeaways(run: dict, *, current_coverage: Mapping[str, Any] | None = None) -> list[dict]:
    runs_dir_value = str(run.get("runs_dir") or "").strip()
    if not runs_dir_value:
        return []
    runs_dir = Path(runs_dir_value)
    if not runs_dir.exists():
        return []

    summaries_by_iter = _iteration_summaries_by_iter(runs_dir)
    handoffs_by_iter = _iteration_handoffs_by_iter(runs_dir)
    iter_ids = sorted(set(summaries_by_iter) | set(handoffs_by_iter))
    current_iter_id = _current_iter_id(run)

    return [
        _build_structured_iteration_takeaway(
            run,
            iter_id=iter_id,
            summary_payload=summaries_by_iter.get(iter_id) or {},
            handoffs=sorted(
                handoffs_by_iter.get(iter_id, []),
                key=_handoff_step_order,
            ),
            current_coverage=current_coverage if iter_id == current_iter_id else None,
        )
        for iter_id in iter_ids
    ]


def _iteration_summaries_by_iter(runs_dir: Path) -> dict[int, dict]:
    summaries_by_iter: dict[int, dict] = {}
    for summary_path in sorted(runs_dir.glob("iterations/iter_*/summary.json")):
        summary_payload = safe_read_json_file(summary_path)
        if not summary_payload:
            continue
        iter_id = _int_value(summary_payload.get("iter"), default=-1)
        if iter_id >= 0:
            summaries_by_iter[iter_id] = summary_payload
    return summaries_by_iter


def _iteration_handoffs_by_iter(runs_dir: Path) -> dict[int, list[dict]]:
    handoffs_by_iter: dict[int, list[dict]] = defaultdict(list)
    for handoff_path in sorted(runs_dir.glob("iterations/iter_*/steps/*/handoff.json")):
        handoff_payload = safe_read_json_file(handoff_path)
        if not handoff_payload:
            continue
        source = handoff_payload.get("source") if isinstance(handoff_payload.get("source"), Mapping) else {}
        iter_id = _int_value(source.get("iter"), default=-1)
        if iter_id >= 0:
            handoffs_by_iter[iter_id].append(handoff_payload)
    return handoffs_by_iter


def _current_iter_id(run: Mapping[str, Any]) -> int | None:
    current_iter = run.get("current_iter")
    return _int_value(current_iter, default=None) if current_iter is not None else None


def _coverage_gap_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
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
                "required": item.get("required") is True,
                "reason": str(item.get("reason") or "").strip(),
                "text": str(item.get("text") or "").strip(),
                "evidence_refs": _string_list(item.get("evidence_refs")),
            }
        )
    return rows[:5]


def _handoff_step_order(handoff: Mapping[str, object]) -> int:
    source = handoff.get("source") if isinstance(handoff.get("source"), Mapping) else {}
    return structured_non_negative_int(source.get("step_order"))


def _build_structured_iteration_takeaway(
    run: Mapping[str, Any],
    *,
    iter_id: int,
    summary_payload: Mapping[str, Any],
    handoffs: list[dict],
    current_coverage: Mapping[str, Any] | None = None,
) -> dict:
    current_iter_id = _current_iter_id(run)
    score_payload = summary_payload.get("score") if isinstance(summary_payload.get("score"), Mapping) else {}
    stagnation_payload = summary_payload.get("stagnation") if isinstance(summary_payload.get("stagnation"), Mapping) else {}
    coverage_fallback = current_coverage if isinstance(current_coverage, Mapping) and not stagnation_payload else {}
    composite_score = score_payload.get("composite")
    roles = [build_role_takeaway_from_handoff(handoff, composite_score=composite_score) for handoff in handoffs]
    primary_role = _primary_role_takeaway(roles)
    summary_text = (
        terminal_task_verdict_summary_for_iteration(run, iter_id=iter_id, current_iter_id=current_iter_id)
        or (primary_role.get("summary") if isinstance(primary_role, Mapping) else "")
        or clean_takeaway_text(run.get("summary_md"), max_length=220)
    )
    return {
        "iter": iter_id,
        "display_iter": display_iter(iter_id),
        "status": _structured_iteration_status(
            run,
            roles=roles,
            score_payload=score_payload,
            iter_id=iter_id,
            current_iter_id=current_iter_id,
        ),
        "phase": str(summary_payload.get("phase") or "").strip(),
        "summary": summary_text,
        "timestamp": str(summary_payload.get("timestamp") or "").strip(),
        "composite_score": composite_score,
        "stagnation_mode": str(stagnation_payload.get("mode") or "none"),
        "evidence_progress_mode": str(
            stagnation_payload.get("evidence_progress_mode")
            or coverage_fallback.get("evidence_progress_mode")
            or "none"
        ),
        "coverage_status": str(stagnation_payload.get("coverage_status") or coverage_fallback.get("status") or "pending"),
        "covered_check_count": _int_value(
            stagnation_payload.get("covered_check_count", coverage_fallback.get("covered_check_count")),
            default=0,
        ),
        "missing_check_count": _int_value(
            stagnation_payload.get("missing_check_count", coverage_fallback.get("missing_check_count")),
            default=0,
        ),
        "covered_check_ids": _string_list(stagnation_payload.get("covered_check_ids") or coverage_fallback.get("covered_check_ids")),
        "missing_check_ids": _string_list(stagnation_payload.get("missing_check_ids") or coverage_fallback.get("missing_check_ids")),
        "coverage_top_gaps": _coverage_gap_list(stagnation_payload.get("coverage_top_gaps") or coverage_fallback.get("top_gaps")),
        "consecutive_no_required_coverage_delta": _int_value(
            stagnation_payload.get("consecutive_no_required_coverage_delta"),
            default=0,
        ),
        "role_count": len(roles),
        "roles": roles,
    }


def _primary_role_takeaway(roles: list[dict]) -> dict | None:
    return next((item for item in roles if item.get("archetype") == "gatekeeper"), roles[-1] if roles else None)


def _structured_iteration_status(
    run: Mapping[str, Any],
    *,
    roles: list[dict],
    score_payload: Mapping[str, Any],
    iter_id: int,
    current_iter_id: int | None,
) -> str:
    terminal_status = terminal_task_verdict_status_for_iteration(run, iter_id=iter_id, current_iter_id=current_iter_id)
    if terminal_status:
        return terminal_status
    passed = score_payload.get("passed")
    status = "pending"
    if passed is True:
        status = "passed"
    elif passed is False:
        status = "blocked"
    elif current_iter_id == iter_id and active_takeaway_run_status(run.get("status")):
        status = "running"
    elif roles:
        status = normalize_takeaway_status(roles[-1].get("status"))
    return status
