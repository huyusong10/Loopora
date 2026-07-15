from __future__ import annotations

from collections.abc import Callable

from loopora.events.envelope import EventEnvelope
from loopora.events.streams import loop_stream_id, run_stream_id
from loopora.projections._event_replay_support import EVENT_REPLAY_PROJECTION_SCHEMA_VERSION
from loopora.projections import replay_loop_projection_bundle, replay_run_projection_bundle
from loopora.utils import coerced_int, coerced_non_negative_int

RUN_PROJECTION_KINDS = {
    "run_snapshot": "event_replayed_run_snapshot",
    "current_step": "event_replayed_current_step",
    "evidence_ledger": "event_replayed_evidence_ledger",
    "coverage": "event_replayed_coverage",
    "task_verdict": "event_replayed_task_verdict",
    "step_surfaces": "event_replayed_step_surfaces",
    "audit_timeline": "event_replayed_audit_timeline",
}
RUN_IDENTITY_PROJECTION_NAMES = frozenset({"run_snapshot", "current_step"})


def replay_run_projections(repository, run_id: str) -> dict:
    return replay_run_projection_bundle(repository.list_domain_events(run_stream_id(run_id)))


def rebuild_run_projection_cache(repository, run_id: str) -> dict:
    return repository.refresh_run_projection_cache(run_id)


def run_projection_bundle_for_run(repository, run_id: str) -> dict:
    latest_sequence = repository.latest_domain_event_sequence(run_stream_id(run_id))
    if latest_sequence <= 0:
        return {}
    bundle: dict[str, dict] = {}
    for projection_name, kind in RUN_PROJECTION_KINDS.items():
        cached = repository.get_projection_record(projection_name, run_id)
        payload = cached.get("payload") if isinstance(cached, dict) else {}
        if not (
            _is_fresh_run_projection_payload(cached, payload, kind=kind, latest_sequence=latest_sequence)
            and _has_expected_run_identity(
                payload,
                run_id=run_id,
                require_run_id=projection_name in RUN_IDENTITY_PROJECTION_NAMES,
            )
        ):
            return rebuild_run_projection_cache(repository, run_id)
        bundle[projection_name] = payload
    return bundle


def current_step_projection_for_run(repository, run_id: str) -> dict:
    cached_payload, _latest_sequence = _fresh_cached_run_projection_payload(
        repository,
        "current_step",
        run_id,
        kind="event_replayed_current_step",
    )
    if cached_payload is not None:
        return cached_payload
    return _rebuilt_run_projection_payload(repository, run_id, "current_step")


def run_snapshot_projection_for_run(repository, run_id: str) -> dict:
    cached_payload, latest_sequence = _fresh_cached_run_projection_payload(
        repository,
        "run_snapshot",
        run_id,
        kind="event_replayed_run_snapshot",
    )
    if cached_payload is not None:
        return cached_payload
    if latest_sequence <= 0:
        return {}
    return _rebuilt_run_projection_payload(repository, run_id, "run_snapshot")


def _fresh_cached_run_projection_payload(
    repository,
    projection_name: str,
    run_id: str,
    *,
    kind: str,
) -> tuple[dict | None, int]:
    latest_sequence = repository.latest_domain_event_sequence(run_stream_id(run_id))
    cached = repository.get_projection_record(projection_name, run_id)
    payload = cached.get("payload") if isinstance(cached, dict) else {}
    if _is_fresh_run_projection_payload(
        cached,
        payload,
        kind=kind,
        latest_sequence=latest_sequence,
    ) and _has_expected_run_identity(
        payload,
        run_id=run_id,
        require_run_id=True,
    ):
        return payload, latest_sequence
    return None, latest_sequence


def _is_fresh_run_projection_payload(
    cached: object,
    payload: object,
    *,
    kind: str,
    latest_sequence: int,
) -> bool:
    cached_record_sequence = coerced_int(cached.get("source_sequence") if isinstance(cached, dict) else None, default=0)
    cached_payload_sequence = coerced_int(payload.get("source_sequence") if isinstance(payload, dict) else None, default=0)
    return (
        isinstance(payload, dict)
        and coerced_int(payload.get("schema_version"), default=0) == EVENT_REPLAY_PROJECTION_SCHEMA_VERSION
        and payload.get("kind") == kind
        and cached_record_sequence > 0
        and cached_payload_sequence > 0
        and cached_record_sequence == latest_sequence
        and cached_payload_sequence == latest_sequence
    )


def _has_expected_run_identity(payload: object, *, run_id: str, require_run_id: bool) -> bool:
    payload_run_id = str(payload.get("run_id") or "").strip() if isinstance(payload, dict) else ""
    return (not payload_run_id and not require_run_id) or payload_run_id == run_id


def _rebuilt_run_projection_payload(repository, run_id: str, projection_name: str) -> dict:
    projections = rebuild_run_projection_cache(repository, run_id)
    payload = projections.get(projection_name) if isinstance(projections, dict) else {}
    return payload if isinstance(payload, dict) else {}


def rebuild_loop_projection_cache_for_connection(event_repository, connection, loop_id: str) -> dict:
    return rebuild_projection_cache_for_connection(
        event_repository,
        connection,
        stream_id=loop_stream_id(loop_id),
        projection_key=loop_id,
        replay_projection_bundle=replay_loop_projection_bundle,
    )


def rebuild_run_projection_cache_for_connection(event_repository, connection, run_id: str) -> dict:
    return rebuild_projection_cache_for_connection(
        event_repository,
        connection,
        stream_id=run_stream_id(run_id),
        projection_key=run_id,
        replay_projection_bundle=replay_run_projection_bundle,
    )


def rebuild_projection_cache_for_connection(
    event_repository,
    connection,
    *,
    stream_id: str,
    projection_key: str,
    replay_projection_bundle: Callable[[list[EventEnvelope]], dict],
) -> dict:
    projections = replay_projection_bundle(event_repository.list_domain_events_for_connection(connection, stream_id))
    for name, payload in projections.items():
        event_repository.put_projection_record_for_connection(
            connection,
            name,
            projection_key,
            source_sequence=coerced_non_negative_int(payload.get("source_sequence")) if isinstance(payload, dict) else 0,
            payload=payload,
        )
    return projections
