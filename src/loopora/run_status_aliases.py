from __future__ import annotations

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
