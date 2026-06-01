from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict

from loopora.run_status_aliases import public_run_status_from_lifecycle
from loopora.run_projection_fields import event_projection_payload, task_verdict_from_run
from loopora.structured_numbers import coerced_optional_non_negative_int
from loopora.strategy_source import (
    normalize_strategy_role_display_name,
    strategy_archetype_display_name,
    strategy_source_from_record,
)

WEB_PROJECTION_SCHEMA_VERSION = 4


class WebRunDetailSummaryV4(TypedDict):
    run_id: str
    loop_id: str
    run_status: str
    task_verdict_status: str
    current_iter: int | None
    active_role: str
    workdir: str


class WebRunDetailTimingV4(TypedDict):
    queued_at: str
    started_at: str
    finished_at: str
    updated_at: str
    created_at: str


class WebRunDetailDisplayV4(TypedDict):
    summary_md: str


class WebRunDetailProgressStageV4(TypedDict):
    key: str
    label: str
    kind: Literal["checks", "strategy_step", "finished"]
    sequence: int


class WebRunDetailLifecycleV4(TypedDict):
    run_id: str
    loop_id: str
    run_status: str
    current_iter: int | None
    active_role: str
    workdir: str


class WebRunDetailProjectionV4(TypedDict):
    schema_version: int
    kind: Literal["web_run_detail"]
    status: str
    strategy_source: dict[str, Any]
    progress_stages: list[WebRunDetailProgressStageV4]
    summary: WebRunDetailSummaryV4
    lifecycle: WebRunDetailLifecycleV4
    task_verdict: dict[str, Any]
    display: WebRunDetailDisplayV4
    timing: WebRunDetailTimingV4
    technical_handoff: dict[str, str]
    diagnostics: dict[str, Any]


def web_run_detail_projection(run: dict[str, Any], event_projections: Mapping[str, Any] | None = None) -> WebRunDetailProjectionV4:
    run_id = str(run.get("id") or "").strip()
    projections = event_projections if isinstance(event_projections, Mapping) else {}
    run_snapshot = event_projection_payload(projections.get("run_snapshot"), kind="event_replayed_run_snapshot")
    strategy_source = _projection_strategy_source(run)
    task_verdict = task_verdict_from_run({**run, "event_projections": projections}) or {"status": "not_evaluated"}
    summary: WebRunDetailSummaryV4 = {
        "run_id": run_id,
        "loop_id": str(run.get("loop_id") or "").strip(),
        "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
        "task_verdict_status": str(task_verdict["status"]),
        "current_iter": coerced_optional_non_negative_int(run.get("current_iter")),
        "active_role": str(run.get("active_role") or "").strip(),
        "workdir": str(run.get("workdir") or "").strip(),
    }
    lifecycle: WebRunDetailLifecycleV4 = {
        "run_id": summary["run_id"],
        "loop_id": summary["loop_id"],
        "run_status": summary["run_status"] or "unknown",
        "current_iter": summary["current_iter"],
        "active_role": summary["active_role"],
        "workdir": summary["workdir"],
    }
    return {
        "schema_version": WEB_PROJECTION_SCHEMA_VERSION,
        "kind": "web_run_detail",
        "status": _run_status_from_projection_or_record(run_snapshot, run),
        "strategy_source": strategy_source,
        "progress_stages": web_run_detail_progress_stages({"strategy_source": strategy_source}),
        "summary": _summary_from_projection_or_record(summary, run_snapshot, task_verdict),
        "lifecycle": _lifecycle_from_projection_or_record(lifecycle, run_snapshot),
        "task_verdict": task_verdict,
        "display": {
            "summary_md": str(run.get("summary_md") or ""),
        },
        "timing": {
            "queued_at": str(run.get("queued_at") or ""),
            "started_at": str(run.get("started_at") or ""),
            "finished_at": str(run.get("finished_at") or ""),
            "updated_at": str(run.get("updated_at") or ""),
            "created_at": str(run.get("created_at") or ""),
        },
        "technical_handoff": {
            "run_url": f"/runs/{run_id}" if run_id else "",
            "events_url": f"/api/runs/{run_id}/events" if run_id else "",
            "observation_snapshot_url": f"/api/runs/{run_id}/observation-snapshot" if run_id else "",
        },
        "diagnostics": {
            "source_shape": "projection_bundle" if run_snapshot else "run_record",
            "projection_role": "web_run_detail",
            "projection_source_sequence": (
                coerced_optional_non_negative_int(run_snapshot.get("source_sequence")) if run_snapshot else None
            ),
        },
    }


def web_run_detail_progress_stages(source: Mapping[str, object] | None) -> list[WebRunDetailProgressStageV4]:
    strategy_source = _projection_strategy_source(source)
    roles = strategy_source.get("roles", []) if isinstance(strategy_source, Mapping) else []
    steps = strategy_source.get("steps", []) if isinstance(strategy_source, Mapping) else []
    role_by_id = {
        str(role.get("id") or "").strip(): role
        for role in roles
        if isinstance(role, Mapping) and str(role.get("id") or "").strip()
    }

    stages: list[WebRunDetailProgressStageV4] = [
        {
            "key": "checks",
            "label": "Checks",
            "kind": "checks",
            "sequence": 1,
        }
    ]
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        step_id = str(step.get("id") or "").strip()
        if not step_id:
            continue
        role = role_by_id.get(str(step.get("role_id") or "").strip(), {})
        archetype = str(role.get("archetype") or "").strip()
        fallback_name = strategy_archetype_display_name(archetype, locale="en") if archetype else step_id
        label = normalize_strategy_role_display_name(str(role.get("name") or "").strip(), archetype) or fallback_name
        stages.append(
            {
                "key": f"step:{step_id}",
                "label": label,
                "kind": "strategy_step",
                "sequence": len(stages) + 1,
            }
        )
    stages.append(
        {
            "key": "finished",
            "label": "Run closed",
            "kind": "finished",
            "sequence": len(stages) + 1,
        }
    )
    return stages


def _summary_from_projection_or_record(
    summary: WebRunDetailSummaryV4,
    run_snapshot: Mapping[str, object],
    task_verdict: Mapping[str, object],
) -> WebRunDetailSummaryV4:
    if not run_snapshot:
        return summary
    return {
        **summary,
        "run_id": str(run_snapshot.get("run_id") or summary["run_id"]),
        "loop_id": str(run_snapshot.get("loop_id") or summary["loop_id"]),
        "run_status": public_run_status_from_lifecycle(run_snapshot.get("lifecycle_status")) or summary["run_status"],
        "task_verdict_status": str(task_verdict.get("status") or summary["task_verdict_status"]),
        "current_iter": coerced_optional_non_negative_int(run_snapshot.get("current_iteration")),
        "active_role": _pending_actor_label(run_snapshot.get("pending_actor")) or summary["active_role"],
    }


def _lifecycle_from_projection_or_record(
    lifecycle: WebRunDetailLifecycleV4,
    run_snapshot: Mapping[str, object],
) -> WebRunDetailLifecycleV4:
    if not run_snapshot:
        return lifecycle
    return {
        **lifecycle,
        "run_id": str(run_snapshot.get("run_id") or lifecycle["run_id"]),
        "loop_id": str(run_snapshot.get("loop_id") or lifecycle["loop_id"]),
        "run_status": public_run_status_from_lifecycle(run_snapshot.get("lifecycle_status")) or lifecycle["run_status"],
        "current_iter": coerced_optional_non_negative_int(run_snapshot.get("current_iteration")),
        "active_role": _pending_actor_label(run_snapshot.get("pending_actor")) or lifecycle["active_role"],
    }


def _run_status_from_projection_or_record(run_snapshot: Mapping[str, object], run: Mapping[str, object]) -> str:
    return (
        public_run_status_from_lifecycle(run_snapshot.get("lifecycle_status"))
        if run_snapshot
        else str(run.get("run_status") or run.get("status") or "unknown").strip()
    ) or "unknown"


def _pending_actor_label(value: object) -> str:
    if not isinstance(value, Mapping):
        return ""
    return str(value.get("id") or value.get("kind") or "").strip()


def _projection_strategy_source(source: Mapping[str, object] | None) -> dict[str, Any]:
    return strategy_source_from_record(source) or {}
