from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypedDict

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


def web_run_detail_projection(run: dict[str, Any]) -> WebRunDetailProjectionV4:
    run_id = str(run.get("id") or "").strip()
    strategy_source = _projection_strategy_source(run)
    task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else run.get("task_verdict_json")
    task_verdict = task_verdict if isinstance(task_verdict, dict) else {}
    task_verdict = {
        **task_verdict,
        "status": str(task_verdict.get("status") or "not_evaluated").strip() or "not_evaluated",
    }
    summary: WebRunDetailSummaryV4 = {
        "run_id": run_id,
        "loop_id": str(run.get("loop_id") or "").strip(),
        "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
        "task_verdict_status": str(task_verdict["status"]),
        "current_iter": _optional_int(run.get("current_iter")),
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
        "status": summary["run_status"] or "unknown",
        "strategy_source": strategy_source,
        "progress_stages": web_run_detail_progress_stages({"strategy_source": strategy_source}),
        "summary": summary,
        "lifecycle": lifecycle,
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
            "source_shape": "run_record",
            "projection_role": "web_run_detail",
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


def _projection_strategy_source(source: Mapping[str, object] | None) -> dict[str, Any]:
    return strategy_source_from_record(source) or {}


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None
