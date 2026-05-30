from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from loopora.kernel.actors import ActorRef


class RunLifecycleStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_ACTOR = "awaiting_actor"
    EVALUATING = "evaluating"
    CLOSED = "closed"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RunState:
    id: str
    loop_id: str
    lifecycle_status: RunLifecycleStatus = RunLifecycleStatus.CREATED
    current_iteration: int = 0
    current_step_id: str | None = None
    pending_actor: ActorRef | None = None
    stop_requested: bool = False
