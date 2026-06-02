from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def test_run_engine_delegates_single_event_projection_refreshes() -> None:
    engine_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_engine.py").read_text(encoding="utf-8")
    event_commands_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_event_commands.py").read_text(
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
    assert "RunnerStepInstructionRequest(" not in engine_source
    assert "runner_step_instruction(" not in engine_source
    assert "RunEventAppend" not in engine_source
    assert "append_run_event_and_rebuild_projection_cache" not in engine_source
    assert "append_step_instruction_and_rebuild_projection_cache" in engine_source
    assert "append_step_commit_and_rebuild_projection_cache" not in engine_source
    assert "append_evidence_acceptance_and_rebuild_projection_cache" in engine_source
    assert "append_coverage_recompute_and_rebuild_projection_cache" in engine_source
    assert "append_verdict_issue_and_rebuild_projection_cache" in engine_source
    assert "append_iteration_start_if_absent_and_rebuild_projection_cache" in engine_source
    assert "append_iteration_completion_if_absent_and_rebuild_projection_cache" in engine_source
    assert "append_runner_step_instruction_and_rebuild_projection_cache" in engine_source
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
    assert "RunnerStepInstructionRequest" not in event_commands_source
    assert "runner_step_instruction" not in event_commands_source
    assert "RunnerStepInstructionRequest" not in step_commands_source
    assert "from loopora.engine.step_instruction import" not in step_commands_source
    assert "instruction = request.instruction" in step_commands_source
    assert "RunEventAppend" in event_commands_source
    assert "append_run_event(" in event_commands_source
    assert "rebuild_run_projection_cache" in event_commands_source
    assert "rebuild_run_projection_cache" in cache_source


def test_run_event_append_refresh_helper_lives_under_event_core() -> None:
    engine_event_commands_path = REPO_ROOT / "src" / "loopora" / "engine" / "run_event_commands.py"
    event_commands_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_event_commands.py").read_text(
        encoding="utf-8"
    )

    assert not engine_event_commands_path.exists()
    assert "def append_run_event_and_rebuild_projection_cache" in event_commands_source
    assert "append_run_event(" in event_commands_source
    assert "rebuild_run_projection_cache(" in event_commands_source


def test_run_event_query_helpers_live_under_event_core() -> None:
    engine_queries_path = REPO_ROOT / "src" / "loopora" / "engine" / "run_event_queries.py"
    event_queries_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_event_queries.py").read_text(
        encoding="utf-8"
    )
    iteration_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_iteration_commands.py").read_text(
        encoding="utf-8"
    )
    step_cursor_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_step_cursor.py").read_text(
        encoding="utf-8"
    )

    assert not engine_queries_path.exists()
    assert "def list_run_events" in event_queries_source
    assert "def find_iteration_event" in event_queries_source
    assert "run_stream_id" in event_queries_source
    assert "from loopora.events.run_event_queries import find_iteration_event" in iteration_commands_source
    assert "from loopora.engine.run_event_queries import" not in iteration_commands_source
    assert "from loopora.events.run_event_queries import list_run_events" in step_cursor_source
    assert "run_stream_id" not in step_cursor_source


def test_core_run_event_payload_codecs_live_under_event_core() -> None:
    engine_payloads_path = REPO_ROOT / "src" / "loopora" / "engine" / "run_event_payloads.py"
    payload_source = (REPO_ROOT / "src" / "loopora" / "events" / "step_instruction_payloads.py").read_text(
        encoding="utf-8"
    )
    run_payloads_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_event_payloads.py").read_text(
        encoding="utf-8"
    )
    step_commands_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_step_commands.py").read_text(
        encoding="utf-8"
    )
    projection_source = (REPO_ROOT / "src" / "loopora" / "projections" / "step_instruction.py").read_text(
        encoding="utf-8"
    )

    assert not engine_payloads_path.exists()
    assert "def step_instruction_event_payload" in payload_source
    assert "def step_instruction_from_event_payload" in payload_source
    assert "def step_instruction_payload" in run_payloads_source
    assert "step_instruction_event_payload(instruction)" in run_payloads_source
    assert "from loopora.events.run_event_payloads import" in step_commands_source
    assert "from loopora.engine.run_event_payloads import" not in step_commands_source
    assert "step_instruction_from_event_payload(event.payload" in projection_source
    assert "RoleSpec(" not in projection_source
    assert "EvidenceScope(" not in projection_source
    assert "ActionPolicy(" not in projection_source
    assert "StepOutputContract(" not in projection_source
