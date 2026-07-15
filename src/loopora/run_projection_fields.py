from __future__ import annotations

from collections.abc import Mapping

from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION
from loopora.utils import coerced_int
from loopora.task_verdict_aliases import public_task_verdict_source, public_task_verdict_status
from loopora.task_verdicts import normalize_task_verdict

from loopora.kernel.run_state import RunLifecycleStatus

LIFECYCLE_TO_PUBLIC_RUN_STATUS = {
    RunLifecycleStatus.CREATED.value: "queued",
    RunLifecycleStatus.RUNNING.value: "running",
    RunLifecycleStatus.AWAITING_ACTOR.value: "awaiting_agent",
    RunLifecycleStatus.EVALUATING.value: "running",
    RunLifecycleStatus.CLOSED.value: "succeeded",
    RunLifecycleStatus.STOPPED.value: "stopped",
    RunLifecycleStatus.FAILED.value: "failed",
}

PUBLIC_RUN_STATUS_TO_LIFECYCLE = {
    "queued": RunLifecycleStatus.CREATED,
    "running": RunLifecycleStatus.RUNNING,
    "awaiting_agent": RunLifecycleStatus.AWAITING_ACTOR,
    "succeeded": RunLifecycleStatus.CLOSED,
    "stopped": RunLifecycleStatus.STOPPED,
    "failed": RunLifecycleStatus.FAILED,
}

def public_run_status_from_lifecycle(value: object) -> str:
    status = str(value or "").strip().lower()
    return LIFECYCLE_TO_PUBLIC_RUN_STATUS.get(status, "")

def lifecycle_status_from_public_run_status(value: object) -> RunLifecycleStatus:
    status = str(value or "").strip().lower()
    return PUBLIC_RUN_STATUS_TO_LIFECYCLE.get(status, RunLifecycleStatus.CREATED)


def projection_first_run_record_fields(event_projections: Mapping[str, object], *, run: Mapping[str, object] | None = None) -> dict:
    fields: dict[str, object] = {}
    run_snapshot = event_projection_payload(event_projections.get("run_snapshot"), kind="event_replayed_run_snapshot")
    task_verdict = _projection_task_verdict(event_projections)
    status = _run_status_from_snapshot(run_snapshot)
    if status:
        fields["run_status"] = status
    if task_verdict and not _record_task_verdict(run):
        fields["task_verdict"] = task_verdict
    return fields


def task_verdict_from_run(run: Mapping[str, object]) -> dict:
    record_verdict = _record_task_verdict(run)
    if record_verdict:
        return record_verdict
    event_projections = run.get("event_projections") if isinstance(run.get("event_projections"), Mapping) else {}
    projected = _projection_task_verdict(event_projections)
    if projected:
        return projected
    return {}


def run_status_from_run(run: Mapping[str, object]) -> str:
    event_projections = run.get("event_projections") if isinstance(run.get("event_projections"), Mapping) else {}
    run_snapshot = event_projection_payload(event_projections.get("run_snapshot"), kind="event_replayed_run_snapshot")
    return _run_status_from_snapshot(run_snapshot) or str(run.get("run_status") or run.get("status") or "").strip()


def _projection_task_verdict(event_projections: Mapping[str, object]) -> dict:
    task_verdict = event_projection_payload(event_projections.get("task_verdict"), kind="event_replayed_task_verdict")
    if not task_verdict:
        return {}
    if not str(task_verdict.get("source") or "").strip():
        return {}
    projected = {
        **task_verdict,
        "status": public_task_verdict_status(task_verdict.get("status")),
        "source": public_task_verdict_source(task_verdict.get("source")),
    }
    normalized = normalize_task_verdict(projected)
    return normalized or {key: value for key, value in projected.items() if value not in ("", [], {})}


def _record_task_verdict(run: Mapping[str, object] | None) -> dict:
    if not isinstance(run, Mapping):
        return {}
    value = run.get("task_verdict") if isinstance(run.get("task_verdict"), Mapping) else run.get("task_verdict_json")
    normalized = normalize_task_verdict(value)
    if normalized:
        return normalized
    if not isinstance(value, Mapping):
        return {}
    status = str(value.get("status") or "").strip()
    if not status:
        return {}
    return dict(value)


def event_projection_payload(value: object, *, kind: str) -> dict:
    if not isinstance(value, Mapping) or value.get("kind") != kind:
        return {}
    if coerced_int(value.get("schema_version"), default=0) != EVENT_REPLAY_PROJECTION_SCHEMA_VERSION:
        return {}
    return dict(value)


def _run_status_from_snapshot(run_snapshot: Mapping[str, object]) -> str:
    if not run_snapshot:
        return ""
    return public_run_status_from_lifecycle(run_snapshot.get("lifecycle_status"))
