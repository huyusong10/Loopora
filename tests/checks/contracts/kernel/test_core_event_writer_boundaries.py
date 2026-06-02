from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def test_event_writers_use_core_event_append_boundary_for_domain_envelopes() -> None:
    engine_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_engine.py").read_text(encoding="utf-8")
    append_source = (REPO_ROOT / "src" / "loopora" / "events" / "append_requests.py").read_text(encoding="utf-8")
    loop_events_source = (REPO_ROOT / "src" / "loopora" / "compiler" / "loop_events.py").read_text(
        encoding="utf-8"
    )
    run_record_events_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_record_events.py").read_text(
        encoding="utf-8"
    )
    loop_records_source = (REPO_ROOT / "src" / "loopora" / "db_loop_records.py").read_text(encoding="utf-8")
    run_records_source = (REPO_ROOT / "src" / "loopora" / "db_run_records.py").read_text(encoding="utf-8")
    run_state_records_source = (REPO_ROOT / "src" / "loopora" / "db_run_state_records.py").read_text(encoding="utf-8")

    assert "DomainEventAppendRequest" not in engine_source
    assert "DomainEventAppendRequest" not in loop_records_source
    assert "DomainEventAppendRequest" not in run_records_source
    assert "DomainEventAppendRequest" not in run_state_records_source
    assert "_append_domain_event_for_connection" not in loop_records_source
    assert "_append_domain_event_for_connection" not in run_records_source
    assert "_append_domain_event_for_connection" not in run_state_records_source
    assert "run_stream_id" not in engine_source
    assert "LoopEventAppend" not in loop_records_source
    assert "append_loop_definition_events_for_connection" in loop_records_source
    assert "append_loop_archived_event_for_connection" in loop_records_source
    assert "LoopEventAppend" in loop_events_source
    assert "RunEventAppend" not in run_records_source
    assert "append_run_created_event_for_connection" in run_records_source
    assert "RunEventAppend" in run_record_events_source
    assert "RunEventAppend" not in run_state_records_source
    assert "append_run_lifecycle_event_for_connection" in run_state_records_source
    assert "append_run_created_event_for_connection" in run_record_events_source
    assert "append_run_lifecycle_event_for_connection" in run_record_events_source
    assert "append_loop_event" not in loop_records_source
    assert "append_loop_event" in loop_events_source
    assert "append_run_event" not in run_records_source
    assert "append_run_event" not in run_state_records_source
    assert "append_run_event" in run_record_events_source
    assert "require_core_event_family" in append_source
    assert "loop_event_append_request" in append_source
    assert "run_event_append_request" in append_source
    assert 'aggregate_type="run"' in append_source
    assert 'aggregate_type="loop"' in append_source
