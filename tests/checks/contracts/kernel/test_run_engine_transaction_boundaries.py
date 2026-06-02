from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]


def test_run_engine_delegates_multi_event_transaction_commands() -> None:
    engine_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_engine.py").read_text(encoding="utf-8")
    engine_artifact_index_path = REPO_ROOT / "src" / "loopora" / "engine" / "run_artifact_index.py"
    event_commands_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_event_commands.py").read_text(
        encoding="utf-8"
    )
    event_artifact_index_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_artifact_index.py").read_text(
        encoding="utf-8"
    )
    event_results_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_event_results.py").read_text(
        encoding="utf-8"
    )
    run_requests_source = (REPO_ROOT / "src" / "loopora" / "engine" / "run_requests.py").read_text(encoding="utf-8")
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
    assert "append_step_commit_and_rebuild_projection_cache" not in engine_source
    assert "append_step_evidence_and_rebuild_projection_cache" in engine_source
    assert "append_domain_event_transaction" not in event_commands_source
    assert "run_event_append_request" not in event_commands_source
    assert "append_step_submission_events" not in event_commands_source
    assert "append_step_evidence_events" not in event_commands_source
    assert "run_snapshot_from_repository" not in event_commands_source
    assert "append_domain_event_transaction" not in evidence_commands_source
    assert "append_domain_event_transaction" not in step_commands_source
    assert "rebuild_run_projection_cache" not in evidence_commands_source
    assert "rebuild_run_projection_cache" not in step_commands_source
    assert "run_event_append_request" not in evidence_commands_source
    assert "run_event_append_request" not in step_commands_source
    assert "append_step_evidence_events(" not in evidence_commands_source
    assert "append_step_submission_events(" not in step_commands_source
    assert "append_step_evidence_events_and_rebuild_projection_cache" in evidence_commands_source
    assert "append_step_submission_events_and_rebuild_projection_cache" in step_commands_source
    assert "from loopora.events.run_evidence_event_transactions import" in evidence_commands_source
    assert "from loopora.events.run_step_event_transactions import" in step_commands_source
    assert "from loopora.events.run_event_transactions import" not in evidence_commands_source
    assert "from loopora.events.run_event_transactions import" not in step_commands_source
    assert "def append_step_commit_and_rebuild_projection_cache" not in step_commands_source
    assert "run_snapshot_from_repository" in step_commands_source
    assert not engine_artifact_index_path.exists()
    assert "def step_result_artifact_index_entries" in event_artifact_index_source
    assert "def evidence_artifact_index_entries" in event_artifact_index_source
    assert "class StepSubmissionEventsResult" in event_results_source
    assert "class StepEvidenceEventsResult" in event_results_source
    assert "RunEngineSubmitStepResult = StepSubmissionEventsResult" in run_requests_source
    assert "RunEngineCommitStepRequest" not in run_requests_source
    assert "RunEngineRecordStepEvidenceResult = StepEvidenceEventsResult" in run_requests_source


def test_run_event_transaction_modules_own_domain_append_boundaries() -> None:
    event_transactions_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_event_transactions.py").read_text(
        encoding="utf-8"
    )
    step_event_transactions_source = (
        REPO_ROOT / "src" / "loopora" / "events" / "run_step_event_transactions.py"
    ).read_text(encoding="utf-8")
    evidence_event_transactions_source = (
        REPO_ROOT / "src" / "loopora" / "events" / "run_evidence_event_transactions.py"
    ).read_text(encoding="utf-8")
    verdict_event_transactions_source = (
        REPO_ROOT / "src" / "loopora" / "events" / "run_verdict_event_transactions.py"
    ).read_text(encoding="utf-8")
    event_transaction_sources = (
        step_event_transactions_source + evidence_event_transactions_source + verdict_event_transactions_source
    )

    assert "from loopora.engine.run_requests import" not in event_transaction_sources
    assert "from loopora.events.run_artifact_index import evidence_artifact_index_entries" in evidence_event_transactions_source
    assert "step_result_artifact_index_entries" in step_event_transactions_source
    assert "StepClaimEventsResult" in step_event_transactions_source
    assert "StepSubmissionEventsResult" in step_event_transactions_source
    assert "StepEvidenceEventsResult" in evidence_event_transactions_source
    assert "VerdictEventsResult" in verdict_event_transactions_source
    assert "run_event_append_request" in event_transaction_sources
    assert "rebuild_run_projection_cache" in event_transaction_sources
    assert "from loopora.engine.run_artifact_index import" not in event_transaction_sources
    assert "from loopora.events.run_step_event_transactions import" in event_transactions_source
    assert "from loopora.events.run_evidence_event_transactions import" in event_transactions_source
    assert "from loopora.events.run_verdict_event_transactions import" in event_transactions_source


def test_run_event_transaction_helpers_live_under_event_core() -> None:
    engine_transactions_path = REPO_ROOT / "src" / "loopora" / "engine" / "run_event_transactions.py"
    event_transactions_source = (REPO_ROOT / "src" / "loopora" / "events" / "run_event_transactions.py").read_text(
        encoding="utf-8"
    )
    step_event_transactions_source = (
        REPO_ROOT / "src" / "loopora" / "events" / "run_step_event_transactions.py"
    ).read_text(encoding="utf-8")
    evidence_event_transactions_source = (
        REPO_ROOT / "src" / "loopora" / "events" / "run_evidence_event_transactions.py"
    ).read_text(encoding="utf-8")
    verdict_event_transactions_source = (
        REPO_ROOT / "src" / "loopora" / "events" / "run_verdict_event_transactions.py"
    ).read_text(encoding="utf-8")

    assert not engine_transactions_path.exists()
    assert "def append_step_claim_events" in step_event_transactions_source
    assert "def append_step_submission_events" in step_event_transactions_source
    assert "def append_evidence_acceptance_event" in evidence_event_transactions_source
    assert "def append_step_evidence_events" in evidence_event_transactions_source
    assert "def append_verdict_events" in verdict_event_transactions_source
    assert "def append_evidence_acceptance_event_and_rebuild_projection_cache" in evidence_event_transactions_source
    assert "def append_step_submission_events_and_rebuild_projection_cache" in step_event_transactions_source
    assert "def append_step_evidence_events_and_rebuild_projection_cache" in evidence_event_transactions_source
    assert "def append_verdict_events_and_rebuild_projection_cache" in verdict_event_transactions_source
    assert "def append_" not in event_transactions_source
