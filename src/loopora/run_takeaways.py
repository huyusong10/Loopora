from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from loopora.run_takeaway_common import (
    LEGACY_RUNTIME_ROLE_TO_ARCHETYPE as LEGACY_RUNTIME_ROLE_TO_ARCHETYPE,
    _int_value,
    clean_takeaway_text as clean_takeaway_text,
    display_iter,
    normalize_takeaway_status,
    summary_excerpt,
)
from loopora.run_takeaway_evidence import (
    build_evidence_coverage,
    build_evidence_manifest,
    build_task_verdict_artifact_path,
    empty_evidence_coverage,
    empty_evidence_manifest,
    normalize_evidence_coverage_payload,
    normalize_evidence_manifest_payload,
)
from loopora.run_takeaway_judgment import (
    build_judgment_contract,
    empty_judgment_contract as empty_judgment_contract,
    normalize_judgment_contract_payload,
)
from loopora.run_takeaway_iterations import (
    build_role_takeaway_from_handoff as build_role_takeaway_from_handoff,
    build_structured_iteration_takeaways,
)
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run
from loopora.task_verdicts import BUCKET_KEYS, normalize_task_verdict




from loopora.run_takeaway_common import (
    _string_value,
    display_role_name,
    safe_read_json_file,
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


class RunTakeawayProjection(TypedDict):
    run_status: str
    task_verdict: dict[str, Any]
    task_verdict_path: str
    judgment_contract: dict[str, Any]
    evidence_buckets: dict[str, Any]
    build_dir: str
    log_dir: str
    evidence_count: int
    evidence_coverage: dict[str, Any]
    evidence_manifest: dict[str, Any]
    iteration_count: int
    role_conclusion_count: int
    latest_display_iter: int | None
    latest_status: str
    latest_summary: str
    iterations: list[dict[str, Any]]
    source_event_id: NotRequired[int]


def build_minimal_run_takeaway_projection(
    run: Mapping[str, Any],
    *,
    source_event_id: int | None = None,
) -> RunTakeawayProjection:
    raw_task_verdict = task_verdict_from_run(run)
    task_verdict = normalize_task_verdict(raw_task_verdict)
    projection: RunTakeawayProjection = {
        "run_status": run_status_from_run(run),
        "task_verdict": dict(task_verdict),
        "task_verdict_path": "",
        "judgment_contract": build_judgment_contract(run),
        "evidence_buckets": _normalize_takeaway_evidence_buckets(raw_task_verdict.get("buckets")),
        "build_dir": str(Path(str(run.get("workdir") or "")).expanduser().resolve()) if run.get("workdir") else "",
        "log_dir": str(Path(str(run.get("runs_dir") or "")).expanduser().resolve()) if run.get("runs_dir") else "",
        "evidence_count": 0,
        "evidence_coverage": empty_evidence_coverage(),
        "evidence_manifest": empty_evidence_manifest(),
        "iteration_count": 0,
        "role_conclusion_count": 0,
        "latest_display_iter": None,
        "latest_status": str(run.get("status") or "").strip(),
        "latest_summary": str(run.get("summary_md") or "").strip()[:240],
        "iterations": [],
    }
    if source_event_id is not None:
        projection["source_event_id"] = _int_value(source_event_id, default=0) or 0
    return projection


def normalize_run_takeaway_projection_shape(
    run: Mapping[str, Any],
    projection: Mapping[str, Any],
    *,
    source_event_id: int | None = None,
) -> RunTakeawayProjection:
    normalized = build_minimal_run_takeaway_projection(
        run,
        source_event_id=source_event_id if source_event_id is not None else _int_value(projection.get("source_event_id"), default=None),
    )
    _apply_takeaway_scalar_projection_fields(normalized, projection)
    _apply_takeaway_task_verdict_projection_fields(normalized, projection)
    _apply_takeaway_judgment_contract_projection_fields(normalized, projection)
    _apply_takeaway_evidence_projection_fields(normalized, projection)
    _apply_takeaway_iteration_projection_fields(normalized, projection)
    return normalized


def _apply_takeaway_scalar_projection_fields(normalized: RunTakeawayProjection, projection: Mapping[str, Any]) -> None:
    if projection.get("run_status") is not None:
        normalized["run_status"] = str(projection.get("run_status") or "").strip()
    if projection.get("build_dir") is not None:
        normalized["build_dir"] = str(projection.get("build_dir") or "")
    if projection.get("log_dir") is not None:
        normalized["log_dir"] = str(projection.get("log_dir") or "")
    if projection.get("latest_status") is not None:
        normalized["latest_status"] = str(projection.get("latest_status") or "")
    if projection.get("latest_summary") is not None:
        normalized["latest_summary"] = str(projection.get("latest_summary") or "")
    if projection.get("task_verdict_path") is not None:
        normalized["task_verdict_path"] = str(projection.get("task_verdict_path") or "")
    if projection.get("source_event_id") is not None:
        normalized["source_event_id"] = _int_value(projection.get("source_event_id"), default=0) or 0


def _apply_takeaway_task_verdict_projection_fields(normalized: RunTakeawayProjection, projection: Mapping[str, Any]) -> None:
    raw_task_verdict = projection.get("task_verdict") if isinstance(projection.get("task_verdict"), Mapping) else {}
    task_verdict = normalize_task_verdict(raw_task_verdict)
    if task_verdict:
        normalized["task_verdict"] = task_verdict
        normalized["evidence_buckets"] = _normalize_takeaway_evidence_buckets(raw_task_verdict.get("buckets"))
    if isinstance(projection.get("evidence_buckets"), Mapping):
        normalized["evidence_buckets"] = _normalize_takeaway_evidence_buckets(projection.get("evidence_buckets"))


def _normalize_takeaway_evidence_buckets(value: object) -> dict[str, list[dict]]:
    if not isinstance(value, Mapping):
        return {}
    buckets: dict[str, list[dict]] = {}
    for key in BUCKET_KEYS:
        if key in value:
            buckets[key] = _takeaway_bucket_list(value.get(key))
    return buckets


def _takeaway_bucket_list(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    result: list[dict] = []
    for item in value:
        if isinstance(item, Mapping):
            result.append(dict(item))
        elif isinstance(item, str) and item.strip():
            result.append({"label": item.strip()})
    return result


def _apply_takeaway_judgment_contract_projection_fields(normalized: RunTakeawayProjection, projection: Mapping[str, Any]) -> None:
    if isinstance(projection.get("judgment_contract"), Mapping):
        normalized["judgment_contract"] = normalize_judgment_contract_payload(projection.get("judgment_contract"))


def _apply_takeaway_evidence_projection_fields(normalized: RunTakeawayProjection, projection: Mapping[str, Any]) -> None:
    normalized["evidence_count"] = _int_value(projection.get("evidence_count"), default=normalized["evidence_count"]) or 0
    if isinstance(projection.get("evidence_coverage"), Mapping):
        normalized["evidence_coverage"] = normalize_evidence_coverage_payload(projection.get("evidence_coverage"))
    if isinstance(projection.get("evidence_manifest"), Mapping):
        normalized["evidence_manifest"] = normalize_evidence_manifest_payload(projection.get("evidence_manifest"))


def _apply_takeaway_iteration_projection_fields(normalized: RunTakeawayProjection, projection: Mapping[str, Any]) -> None:
    normalized["iteration_count"] = _int_value(projection.get("iteration_count"), default=normalized["iteration_count"]) or 0
    normalized["role_conclusion_count"] = _int_value(projection.get("role_conclusion_count"), default=normalized["role_conclusion_count"]) or 0
    normalized["latest_display_iter"] = _int_value(projection.get("latest_display_iter"), default=normalized["latest_display_iter"])
    if isinstance(projection.get("iterations"), list):
        normalized["iterations"] = [dict(item) for item in projection.get("iterations") or [] if isinstance(item, Mapping)]


def build_run_key_takeaways(run: dict) -> RunTakeawayProjection:
    evidence_coverage = build_evidence_coverage(run)
    iterations = build_structured_iteration_takeaways(run, current_coverage=evidence_coverage)
    if not iterations:
        legacy_iteration = build_legacy_iteration_takeaway(run)
        if legacy_iteration:
            iterations = [legacy_iteration]
    iterations = sorted(iterations, key=_iteration_sort_key, reverse=True)
    latest = iterations[0] if iterations else None
    evidence_count = 0
    runs_dir_value = str(run.get("runs_dir") or "").strip()
    if runs_dir_value:
        evidence_count = len(read_jsonl(RunArtifactLayout(Path(runs_dir_value)).evidence_ledger_path))
    evidence_manifest = build_evidence_manifest(run)
    projection = build_minimal_run_takeaway_projection(run)
    projection.update(
        {
            "task_verdict_path": build_task_verdict_artifact_path(run),
            "judgment_contract": build_judgment_contract(run),
            "evidence_count": evidence_count,
            "evidence_coverage": evidence_coverage,
            "evidence_manifest": evidence_manifest,
            "iteration_count": len(iterations),
            "role_conclusion_count": sum(len(list(iteration.get("roles") or [])) for iteration in iterations),
            "latest_display_iter": latest.get("display_iter") if latest else None,
            "latest_status": latest.get("status") if latest else normalize_takeaway_status(run.get("status")),
            "latest_summary": latest.get("summary") if latest else summary_excerpt(run.get("summary_md")),
            "iterations": iterations,
        }
    )
    return projection


def _iteration_sort_key(item: Mapping[str, Any]) -> int:
    iter_id = _int_value(item.get("iter"), default=None)
    return iter_id if iter_id is not None else -1


_build_run_key_takeaways = build_run_key_takeaways
_build_evidence_coverage = build_evidence_coverage
_build_evidence_manifest = build_evidence_manifest
_display_iter = display_iter
_summary_excerpt = summary_excerpt
