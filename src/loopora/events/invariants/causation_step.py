from __future__ import annotations

import sqlite3

from loopora.events.invariants.common import json_dict, latest_event_row
from loopora.events.store import DomainEventAppendRequest


def require_step_result_event_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run":
        return
    required_source = {
        "StepAccepted": "StepSubmitted",
        "StepSubmissionRejected": "StepSubmitted",
        "StepCommitted": "StepAccepted",
    }.get(request.event_type)
    if required_source is None:
        return
    row = latest_event_row(connection, request.stream_id, required_source)
    if row is None:
        raise ValueError(f"{request.event_type} requires prior {required_source}")
    if request.causation_id != row["event_id"]:
        raise ValueError(f"{request.event_type} requires causation_id to reference latest {required_source}")
    _require_step_submission_decision_is_open(connection, request)
    _require_step_acceptance_commit_is_open(connection, request)
    _require_step_result_payload_matches_source(request, source_payload=json_dict(row["payload_json"]))


def require_strategy_advanced_causation(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.aggregate_type != "run" or request.event_type != "StrategyAdvanced":
        return
    committed_row = latest_event_row(connection, request.stream_id, "StepCommitted")
    if committed_row is None:
        raise ValueError("StrategyAdvanced requires prior StepCommitted")
    if request.causation_id != committed_row["event_id"]:
        raise ValueError("StrategyAdvanced requires causation_id to reference latest StepCommitted")
    existing_row = connection.execute(
        """
        SELECT event_type FROM event_store
        WHERE stream_id = ?
          AND causation_id = ?
          AND event_type = 'StrategyAdvanced'
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if existing_row is not None:
        raise ValueError("StepCommitted already advanced strategy")
    committed_payload = json_dict(committed_row["payload_json"])
    _require_step_result_payload_matches_source(request, source_payload=committed_payload)
    result_status = str((request.payload or {}).get("result_status") or "").strip()
    committed_result_status = str(committed_payload.get("result_status") or "").strip()
    if result_status != committed_result_status:
        raise ValueError("StrategyAdvanced requires result_status to match causation event")
    if str((request.payload or {}).get("reason") or "").strip() != "step_committed":
        raise ValueError("StrategyAdvanced requires reason step_committed")


def _require_step_submission_decision_is_open(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.event_type not in {"StepAccepted", "StepSubmissionRejected"} or not request.causation_id:
        return
    row = connection.execute(
        """
        SELECT event_type FROM event_store
        WHERE stream_id = ?
          AND causation_id = ?
          AND event_type IN ('StepAccepted', 'StepSubmissionRejected')
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if row is not None:
        raise ValueError("StepSubmitted already has accepted or rejected decision")


def _require_step_acceptance_commit_is_open(
    connection: sqlite3.Connection,
    request: DomainEventAppendRequest,
) -> None:
    if request.event_type != "StepCommitted" or not request.causation_id:
        return
    row = connection.execute(
        """
        SELECT event_type FROM event_store
        WHERE stream_id = ?
          AND causation_id = ?
          AND event_type = 'StepCommitted'
        ORDER BY sequence DESC
        LIMIT 1
        """,
        (request.stream_id, request.causation_id),
    ).fetchone()
    if row is not None:
        raise ValueError("StepAccepted already has committed result")


def _require_step_result_payload_matches_source(request: DomainEventAppendRequest, *, source_payload: dict) -> None:
    payload = request.payload or {}
    source_step_id = str(source_payload.get("step_id") or "").strip()
    step_id = str(payload.get("step_id") or "").strip()
    if not step_id or not source_step_id or step_id != source_step_id:
        raise ValueError(f"{request.event_type} requires step_id to match causation event")
    source_iteration = source_payload.get("iteration")
    iteration = payload.get("iteration")
    if source_iteration is not None and iteration is not None and str(iteration) != str(source_iteration):
        raise ValueError(f"{request.event_type} requires iteration to match causation event")
