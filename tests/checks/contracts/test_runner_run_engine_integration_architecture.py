from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_runner_execution_submits_steps_through_run_engine() -> None:
    source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")

    assert "RunEngineSubmitStepRequest" in source
    assert ".submit_step(" in source
    assert "RunEngineCommitStepRequest" not in source
    assert ".commit_step(" not in source


def test_runner_execution_submits_step_before_recording_step_evidence() -> None:
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    iteration_source = (REPO_ROOT / "src" / "loopora" / "service_runner_iteration_state.py").read_text(encoding="utf-8")
    artifacts_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_artifacts.py").read_text(encoding="utf-8")
    evidence_adapter_source = (REPO_ROOT / "src" / "loopora" / "engine" / "evidence_engine_adapter.py").read_text(
        encoding="utf-8"
    )

    assert "RunEngineRecordStepEvidenceRequest" in commit_source
    assert ".record_step_evidence(" in commit_source
    assert commit_source.index(".submit_step(") < commit_source.index(".record_step_evidence(")
    assert "RunEngineAcceptEvidenceRequest" not in commit_source
    assert "RunEngineCoverageRecomputedRequest" not in commit_source
    assert ".accept_evidence(" not in commit_source
    assert ".recompute_coverage(" not in commit_source
    assert "RunEngineRecordStepEvidenceRequest" not in iteration_source
    assert ".record_step_evidence(" not in iteration_source
    assert "write_runner_step_evidence_artifacts" in artifacts_source
    assert "write_evidence_coverage_projection" not in artifacts_source
    assert "write_evidence_manifest_projection" not in artifacts_source
    assert "write_evidence_coverage_projection" in evidence_adapter_source
    assert "write_evidence_manifest_projection" in evidence_adapter_source


def test_run_finalization_uses_stable_verdict_engine_actor_factory() -> None:
    finalization_source = (REPO_ROOT / "src" / "loopora" / "service_run_finalization.py").read_text(encoding="utf-8")
    verdicts_source = (REPO_ROOT / "src" / "loopora" / "run_finalization_verdicts.py").read_text(encoding="utf-8")
    actors_source = (REPO_ROOT / "src" / "loopora" / "kernel" / "actors.py").read_text(encoding="utf-8")
    contracts_source = design_boundary_source()

    assert "ActorRef.verdict_engine()" in finalization_source
    assert 'ActorRef(kind="system", id="verdict-engine"' not in finalization_source
    assert "def verdict_engine" in actors_source
    assert 'id="verdict-engine"' in actors_source
    assert "from loopora.run_finalization_verdicts import" in finalization_source
    assert "def kernel_event_verdict_for_finalization" in verdicts_source
    assert "def event_verdict_for_finalization" in verdicts_source
    assert "verdict_from_legacy_coverage_projection" in verdicts_source
    assert "verdict_from_legacy_coverage_projection" not in finalization_source
    assert "run_finalization_verdicts.py" in contracts_source
