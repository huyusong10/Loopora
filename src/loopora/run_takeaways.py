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
from loopora.run_takeaway_legacy import build_legacy_iteration_takeaway
from loopora.run_projection_fields import run_status_from_run, task_verdict_from_run
from loopora.task_verdicts import BUCKET_KEYS, normalize_task_verdict


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
