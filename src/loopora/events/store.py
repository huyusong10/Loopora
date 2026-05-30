from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Protocol, TypeVar

from loopora.events.envelope import EventEnvelope
from loopora.kernel.actors import ActorRef

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class DomainEventAppendRequest:
    stream_id: str
    aggregate_type: str
    aggregate_id: str
    event_type: str
    payload: dict = field(default_factory=dict)
    actor: ActorRef | None = None
    correlation_id: str = ""
    causation_id: str | None = None
    schema_version: int = 1


class DomainEventStore(Protocol):
    def append_domain_event(self, request: DomainEventAppendRequest) -> EventEnvelope:
        ...

    def append_domain_event_transaction(self, handler: Callable[[DomainEventTransaction], T]) -> T:
        ...

    def list_domain_events(self, stream_id: str, *, after_sequence: int = 0, limit: int = 5000) -> list[EventEnvelope]:
        ...

    def latest_domain_event_sequence(self, stream_id: str) -> int:
        ...


class DomainEventTransaction(Protocol):
    def append_domain_event(self, request: DomainEventAppendRequest) -> EventEnvelope:
        ...

    def record_artifact_index(self, payload: dict) -> dict:
        ...
