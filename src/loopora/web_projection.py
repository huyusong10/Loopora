from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

WEB_PROJECTION_SCHEMA_VERSION = 3


class WebRunDetailSummaryV3(TypedDict):
    run_id: str
    loop_id: str
    run_status: str
    task_verdict_status: str
    current_iter: int | None
    active_role: str
    workdir: str


class WebRunDetailProjectionV3(TypedDict):
    schema_version: int
    kind: Literal["web_run_detail"]
    status: str
    summary: WebRunDetailSummaryV3
    technical_handoff: dict[str, str]
    diagnostics: dict[str, Any]
    raw: NotRequired[dict[str, Any]]


def web_run_detail_projection(run: dict[str, Any]) -> WebRunDetailProjectionV3:
    run_id = str(run.get("id") or "").strip()
    task_verdict = run.get("task_verdict") if isinstance(run.get("task_verdict"), dict) else run.get("task_verdict_json")
    task_verdict = task_verdict if isinstance(task_verdict, dict) else {}
    summary: WebRunDetailSummaryV3 = {
        "run_id": run_id,
        "loop_id": str(run.get("loop_id") or "").strip(),
        "run_status": str(run.get("run_status") or run.get("status") or "").strip(),
        "task_verdict_status": str(task_verdict.get("status") or "not_evaluated").strip() or "not_evaluated",
        "current_iter": _optional_int(run.get("current_iter")),
        "active_role": str(run.get("active_role") or "").strip(),
        "workdir": str(run.get("workdir") or "").strip(),
    }
    return {
        "schema_version": WEB_PROJECTION_SCHEMA_VERSION,
        "kind": "web_run_detail",
        "status": summary["run_status"] or "unknown",
        "summary": summary,
        "technical_handoff": {
            "run_url": f"/runs/{run_id}" if run_id else "",
            "events_url": f"/api/runs/{run_id}/events" if run_id else "",
            "observation_snapshot_url": f"/api/runs/{run_id}/observation-snapshot" if run_id else "",
        },
        "diagnostics": {
            "raw_shape": "run_record",
            "projection_role": "web_run_detail",
        },
        "raw": {"run": run},
    }


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
