from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from loopora.run_takeaway_common import (
    LEGACY_RUNTIME_ROLE_TO_ARCHETYPE,
    _int_value,
    _string_value,
    clean_takeaway_text,
    display_iter,
    display_role_name,
    normalize_takeaway_status,
    safe_read_json_file,
    summary_excerpt,
)


def build_legacy_iteration_takeaway(run: dict) -> dict | None:
    runs_dir_value = str(run.get("runs_dir") or "").strip()
    runs_dir = Path(runs_dir_value) if runs_dir_value else None
    verdict = _legacy_verdict(run, runs_dir)
    excerpt = summary_excerpt(run.get("summary_md"))
    roles = _legacy_failure_roles(verdict)
    if verdict:
        roles.append(_legacy_gatekeeper_role(verdict, step_order=len(roles), excerpt=excerpt))

    if not roles and not excerpt:
        return None

    run_status = str(run.get("status") or "").strip().lower()
    iter_id = _int_value(run.get("current_iter"), default=0) or 0
    return {
        "iter": iter_id,
        "display_iter": display_iter(iter_id) or 1,
        "status": _legacy_iteration_status(run_status, verdict, roles),
        "phase": run_status,
        "summary": excerpt or clean_takeaway_text(verdict.get("decision_summary"), max_length=220),
        "timestamp": "",
        "composite_score": verdict.get("composite_score"),
        "stagnation_mode": "none",
        "evidence_progress_mode": "none",
        "coverage_status": "pending",
        "covered_check_count": 0,
        "missing_check_count": 0,
        "covered_check_ids": [],
        "missing_check_ids": [],
        "coverage_top_gaps": [],
        "consecutive_no_required_coverage_delta": 0,
        "role_count": len(roles),
        "roles": roles,
    }


def _legacy_verdict(run: Mapping[str, Any], runs_dir: Path | None) -> Mapping[str, Any]:
    verdict = run.get("last_verdict_json") if isinstance(run.get("last_verdict_json"), Mapping) else {}
    if verdict or runs_dir is None:
        return verdict
    return safe_read_json_file(runs_dir / "verifier_verdict.json") or safe_read_json_file(runs_dir / "gatekeeper_verdict.json") or {}


def _legacy_failure_roles(verdict: Mapping[str, Any]) -> list[dict]:
    priority_failures = verdict.get("priority_failures") if isinstance(verdict.get("priority_failures"), list) else []
    return [
        _legacy_failure_role(failure, index=index, verdict=verdict) for index, failure in enumerate(priority_failures, start=1) if isinstance(failure, Mapping)
    ]


def _legacy_failure_role(failure: Mapping[str, Any], *, index: int, verdict: Mapping[str, Any]) -> dict:
    runtime_role = _string_value(failure.get("role")).lower()
    return {
        "id": f"legacy-failure-{index}",
        "step_id": "",
        "step_order": index - 1,
        "role_name": display_role_name("", runtime_role=runtime_role),
        "archetype": LEGACY_RUNTIME_ROLE_TO_ARCHETYPE.get(runtime_role, ""),
        "status": "failed",
        "summary": "Execution aborted before this role could produce a stable handoff.",
        "blocking_item": " · ".join(_legacy_failure_support_bits(failure)),
        "next_action": _legacy_feedback(verdict),
        "composite_score": None,
    }


def _legacy_failure_support_bits(failure: Mapping[str, Any]) -> list[str]:
    support_bits = []
    error_code = clean_takeaway_text(failure.get("error_code"), max_length=80)
    attempts = _int_value(failure.get("attempts"), default=None)
    degraded = failure.get("degraded") is True
    if error_code:
        support_bits.append(error_code)
    if attempts is not None:
        support_bits.append(f"attempts={attempts}")
    if degraded:
        support_bits.append("degraded")
    return support_bits


def _legacy_gatekeeper_role(verdict: Mapping[str, Any], *, step_order: int, excerpt: str) -> dict:
    return {
        "id": "legacy-gatekeeper",
        "step_id": "",
        "step_order": step_order,
        "role_name": "GateKeeper",
        "archetype": "gatekeeper",
        "status": "passed" if verdict.get("passed") is True else "blocked",
        "summary": clean_takeaway_text(verdict.get("decision_summary"), max_length=220) or excerpt,
        "blocking_item": _legacy_blocking_note(verdict),
        "next_action": _legacy_feedback(verdict),
        "composite_score": verdict.get("composite_score"),
    }


def _legacy_blocking_note(verdict: Mapping[str, Any]) -> str:
    for item in [
        *_legacy_verdict_string_list(verdict.get("blocking_issues")),
        *_legacy_verdict_string_list(verdict.get("hard_constraint_violations")),
    ]:
        text = clean_takeaway_text(item, max_length=140)
        if text:
            return text
    return ""


def _legacy_verdict_string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _legacy_feedback(verdict: Mapping[str, Any]) -> str:
    return clean_takeaway_text(
        verdict.get("feedback_to_builder") or verdict.get("feedback_to_generator"),
        max_length=520,
    )


def _legacy_iteration_status(run_status: str, verdict: Mapping[str, Any], roles: list[dict]) -> str:
    status = normalize_takeaway_status(run_status)
    if verdict.get("passed") is True:
        status = "passed"
    elif run_status == "running":
        status = "running"
    elif roles and roles[0].get("status") == "failed":
        status = "failed"
    elif verdict:
        status = "blocked"
    return status
