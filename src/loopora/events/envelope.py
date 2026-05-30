from __future__ import annotations

from dataclasses import dataclass, field

from loopora.kernel.actors import ActorRef


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event_id: str
    stream_id: str
    aggregate_type: str
    aggregate_id: str
    sequence: int
    event_type: str
    schema_version: int
    occurred_at: str
    actor: ActorRef
    correlation_id: str
    causation_id: str | None = None
    payload: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return {
            "event_id": self.event_id,
            "stream_id": self.stream_id,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "sequence": self.sequence,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "occurred_at": self.occurred_at,
            "actor": self.actor.to_dict(),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_record(cls, record: dict) -> EventEnvelope:
        return cls(
            event_id=str(record.get("event_id") or ""),
            stream_id=str(record.get("stream_id") or ""),
            aggregate_type=str(record.get("aggregate_type") or ""),
            aggregate_id=str(record.get("aggregate_id") or ""),
            sequence=int(record.get("sequence") or 0),
            event_type=str(record.get("event_type") or ""),
            schema_version=int(record.get("schema_version") or 1),
            occurred_at=str(record.get("occurred_at") or ""),
            actor=ActorRef.from_dict(record.get("actor")),
            correlation_id=str(record.get("correlation_id") or ""),
            causation_id=str(record.get("causation_id") or "") or None,
            payload=dict(record.get("payload") or {}),
        )
