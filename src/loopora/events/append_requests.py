from __future__ import annotations

from dataclasses import dataclass, field

from loopora.events.schemas import require_core_event_family
from loopora.events.store import DomainEventAppendRequest
from loopora.events.streams import loop_stream_id, run_stream_id
from loopora.kernel.actors import ActorRef


@dataclass(frozen=True, slots=True)
class LoopEventAppend:
    loop_id: str
    event_type: str
    payload: dict = field(default_factory=dict)
    actor: ActorRef | None = None
    correlation_id: str = ""
    causation_id: str | None = None
    schema_version: int = 1


@dataclass(frozen=True, slots=True)
class RunEventAppend:
    run_id: str
    event_type: str
    payload: dict = field(default_factory=dict)
    actor: ActorRef | None = None
    correlation_id: str = ""
    causation_id: str | None = None
    schema_version: int = 1


def loop_event_append_request(request: LoopEventAppend) -> DomainEventAppendRequest:
    require_core_event_family(request.event_type, "loop")
    return DomainEventAppendRequest(
        stream_id=loop_stream_id(request.loop_id),
        aggregate_type="loop",
        aggregate_id=request.loop_id,
        event_type=request.event_type,
        payload=request.payload,
        actor=request.actor,
        correlation_id=request.correlation_id,
        causation_id=request.causation_id,
        schema_version=request.schema_version,
    )


def run_event_append_request(request: RunEventAppend) -> DomainEventAppendRequest:
    require_core_event_family(request.event_type, "run")
    return DomainEventAppendRequest(
        stream_id=run_stream_id(request.run_id),
        aggregate_type="run",
        aggregate_id=request.run_id,
        event_type=request.event_type,
        payload=request.payload,
        actor=request.actor,
        correlation_id=request.correlation_id,
        causation_id=request.causation_id,
        schema_version=request.schema_version,
    )


def append_loop_event(event_store, request: LoopEventAppend):
    return event_store.append_domain_event(loop_event_append_request(request))


def append_run_event(event_store, request: RunEventAppend):
    return event_store.append_domain_event(run_event_append_request(request))
