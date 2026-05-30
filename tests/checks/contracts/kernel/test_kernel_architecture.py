from __future__ import annotations

import ast
from pathlib import Path

from loopora.events import CORE_EVENT_AGGREGATE_TYPES, CORE_EVENT_TYPES


REPO_ROOT = Path(__file__).resolve().parents[4]
FORBIDDEN_CORE_IMPORT_PREFIXES = (
    "fastapi",
    "typer",
    "loopora.web",
    "loopora.web_route",
    "loopora.cli",
    "loopora.agent_adapter",
    "loopora.agent_native",
    "loopora.service",
)


def test_kernel_events_and_projections_do_not_depend_on_surfaces_or_adapters() -> None:
    offenders: list[tuple[str, str]] = []
    for directory in ("src/loopora/kernel", "src/loopora/events", "src/loopora/projections", "src/loopora/runners"):
        for path in sorted((REPO_ROOT / directory).glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    offenders.extend(
                        (str(path.relative_to(REPO_ROOT)), alias.name)
                        for alias in node.names
                        if alias.name.startswith(FORBIDDEN_CORE_IMPORT_PREFIXES)
                    )
                elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(FORBIDDEN_CORE_IMPORT_PREFIXES):
                    offenders.append((str(path.relative_to(REPO_ROOT)), node.module))

    assert offenders == []


def test_event_replay_projection_modules_are_split_by_read_model() -> None:
    projection_dir = REPO_ROOT / "src" / "loopora" / "projections"

    assert (projection_dir / "evidence_ledger.py").exists()
    assert (projection_dir / "evidence_coverage.py").exists()
    assert (projection_dir / "run_snapshot.py").exists()
    assert (projection_dir / "current_step.py").exists()
    assert (projection_dir / "loop_definition.py").exists()
    assert (projection_dir / "task_verdict.py").exists()
    assert (projection_dir / "audit_timeline.py").exists()


def test_event_core_owns_projection_cache_replay_writes() -> None:
    cache_source = (REPO_ROOT / "src" / "loopora" / "events" / "projection_cache.py").read_text(encoding="utf-8")
    loop_records_source = (REPO_ROOT / "src" / "loopora" / "db_loop_records.py").read_text(encoding="utf-8")
    run_state_records_source = (REPO_ROOT / "src" / "loopora" / "db_run_state_records.py").read_text(encoding="utf-8")
    run_snapshot_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_snapshot_source.py").read_text(
        encoding="utf-8"
    )
    engine_projection_cache = REPO_ROOT / "src" / "loopora" / "engine" / "run_projection_cache.py"

    assert "replay_loop_projection_bundle" in cache_source
    assert "replay_run_projection_bundle" in cache_source
    assert "current_step_projection_for_run" in cache_source
    assert "run_snapshot_projection_for_run" in cache_source
    assert not engine_projection_cache.exists()
    assert "put_projection_record_for_connection" in cache_source
    assert "SELECT * FROM event_store" not in loop_records_source
    assert "SELECT * FROM event_store" not in run_state_records_source
    assert "_put_projection_record_for_connection" not in loop_records_source
    assert "_put_projection_record_for_connection" not in run_state_records_source
    assert "replay_loop_definition_projection" not in loop_records_source
    assert "replay_run_projection_bundle" not in run_state_records_source
    assert "get_projection_record" not in run_snapshot_source
    assert "list_domain_events" not in run_snapshot_source


def test_core_event_schema_excludes_surface_observability_events() -> None:
    surface_events = {
        "WebPageOpened",
        "AgentCommandRendered",
        "CliJsonPrinted",
        "HostTraceObserved",
        "TodoUpdated",
        "AdapterCheckPassed",
        "StatuslineRead",
    }

    assert CORE_EVENT_TYPES.isdisjoint(surface_events)


def test_core_event_schema_binds_event_types_to_aggregate_families() -> None:
    schemas_source = (REPO_ROOT / "src" / "loopora" / "events" / "schemas.py").read_text(encoding="utf-8")
    append_source = (REPO_ROOT / "src" / "loopora" / "events" / "append_requests.py").read_text(encoding="utf-8")
    db_event_source = (REPO_ROOT / "src" / "loopora" / "db_domain_event_records.py").read_text(encoding="utf-8")

    assert set(CORE_EVENT_AGGREGATE_TYPES) == CORE_EVENT_TYPES
    assert CORE_EVENT_AGGREGATE_TYPES["LoopActivated"] == "loop"
    assert CORE_EVENT_AGGREGATE_TYPES["RunStarted"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["StepInstructionIssued"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["EvidenceAccepted"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["VerdictIssued"] == "run"
    assert CORE_EVENT_AGGREGATE_TYPES["IterationStarted"] == "run"
    assert "def require_core_event_family" in schemas_source
    assert "require_core_event_family" in append_source
    assert "require_core_event_family" in db_event_source


def test_run_engine_uses_public_event_store_boundary_for_atomic_writes() -> None:
    source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_engine.py").read_text(encoding="utf-8")

    assert "._append_domain_event_for_connection" not in source


def test_run_engine_delegates_legacy_lifecycle_state_updates() -> None:
    engine_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_engine.py").read_text(encoding="utf-8")
    lifecycle_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_lifecycle_commands.py").read_text(
        encoding="utf-8"
    )
    lifecycle_updates_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_lifecycle_updates.py").read_text(
        encoding="utf-8"
    )

    assert "update_run(" not in engine_source
    assert "utc_now" not in engine_source
    assert "RunLifecycleStatus" not in engine_source
    assert "VerdictStatus" not in engine_source
    assert "mark_run_started" not in engine_source
    assert "mark_run_succeeded" not in engine_source
    assert "start_run" in engine_source
    assert "advance_run" in engine_source
    assert "mark_run_started" in lifecycle_commands_source
    assert "mark_run_succeeded" in lifecycle_commands_source
    assert "RunLifecycleStatus" in lifecycle_commands_source
    assert "VerdictStatus" in lifecycle_commands_source
    assert "update_run(" in lifecycle_updates_source
    assert 'status="running"' in lifecycle_updates_source
    assert 'status="succeeded"' in lifecycle_updates_source


def test_run_engine_delegates_single_event_projection_refreshes() -> None:
    engine_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_engine.py").read_text(encoding="utf-8")
    event_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_event_commands.py").read_text(
        encoding="utf-8"
    )
    evidence_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_evidence_commands.py").read_text(
        encoding="utf-8"
    )
    iteration_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_iteration_commands.py").read_text(
        encoding="utf-8"
    )
    step_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_step_commands.py").read_text(
        encoding="utf-8"
    )
    verdict_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_verdict_commands.py").read_text(
        encoding="utf-8"
    )
    cache_source = (REPO_ROOT / "src" / "loopora" / "events" / "projection_cache.py").read_text(encoding="utf-8")

    assert "append_domain_event(" not in engine_source
    assert "append_run_event(" not in engine_source
    assert "def replay_projections" not in engine_source
    assert "def current_step_projection" not in engine_source
    assert "def rebuild_projection_cache" not in engine_source
    assert "find_iteration_event" not in engine_source
    assert "def _iteration_event" not in engine_source
    assert "run_event_payloads" not in engine_source
    assert "from loopora.engine.step_instruction" not in engine_source
    assert "WorkflowStepInstructionRequest(" not in engine_source
    assert "workflow_step_instruction(" not in engine_source
    assert "RunEventAppend" not in engine_source
    assert "append_run_event_and_rebuild_projection_cache" not in engine_source
    assert "append_step_instruction_and_rebuild_projection_cache" in engine_source
    assert "append_step_commit_and_rebuild_projection_cache" in engine_source
    assert "append_evidence_acceptance_and_rebuild_projection_cache" in engine_source
    assert "append_coverage_recompute_and_rebuild_projection_cache" in engine_source
    assert "append_verdict_issue_and_rebuild_projection_cache" in engine_source
    assert "append_iteration_start_if_absent_and_rebuild_projection_cache" in engine_source
    assert "append_iteration_completion_if_absent_and_rebuild_projection_cache" in engine_source
    assert "append_workflow_step_instruction_and_rebuild_projection_cache" in engine_source
    assert "find_iteration_event" not in event_commands_source
    assert "append_iteration_start_and_rebuild_projection_cache" not in event_commands_source
    assert "append_iteration_completion_and_rebuild_projection_cache" not in event_commands_source
    assert "find_iteration_event" in iteration_commands_source
    assert "append_iteration_start_and_rebuild_projection_cache" in iteration_commands_source
    assert "append_iteration_completion_and_rebuild_projection_cache" in iteration_commands_source
    assert "run_event_payloads" not in event_commands_source
    assert "evidence_accepted_payload" not in event_commands_source
    assert "coverage_recomputed_payload" not in event_commands_source
    assert "evidence_accepted_payload" in evidence_commands_source
    assert "coverage_recomputed_payload" in evidence_commands_source
    assert "verdict_issued_payload" not in event_commands_source
    assert "verdict_issued_payload" in verdict_commands_source
    assert "WorkflowStepInstructionRequest" not in event_commands_source
    assert "workflow_step_instruction" not in event_commands_source
    assert "WorkflowStepInstructionRequest" in step_commands_source
    assert "workflow_step_instruction" in step_commands_source
    assert "RunEventAppend" in event_commands_source
    assert "append_run_event(" in event_commands_source
    assert "rebuild_run_projection_cache" in event_commands_source
    assert "rebuild_run_projection_cache" in cache_source


def test_run_engine_delegates_multi_event_transaction_commands() -> None:
    engine_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_engine.py").read_text(encoding="utf-8")
    event_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_event_commands.py").read_text(
        encoding="utf-8"
    )
    evidence_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_evidence_commands.py").read_text(
        encoding="utf-8"
    )
    step_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_step_commands.py").read_text(
        encoding="utf-8"
    )

    assert "append_domain_event_transaction" not in engine_source
    assert "run_event_append_request" not in engine_source
    assert "append_step_submission_events" not in engine_source
    assert "append_step_evidence_events" not in engine_source
    assert "self.snapshot(result.run_id)" not in engine_source
    assert "append_step_submission_and_rebuild_projection_cache" in engine_source
    assert "append_step_evidence_and_rebuild_projection_cache" in engine_source
    assert "append_domain_event_transaction" not in event_commands_source
    assert "run_event_append_request" not in event_commands_source
    assert "append_step_submission_events" not in event_commands_source
    assert "append_step_evidence_events" not in event_commands_source
    assert "run_snapshot_from_repository" not in event_commands_source
    assert "append_step_evidence_events" in evidence_commands_source
    assert "run_event_append_request" in evidence_commands_source
    assert "append_step_submission_events" in step_commands_source
    assert "run_event_append_request" in step_commands_source
    assert "run_snapshot_from_repository" in step_commands_source


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
