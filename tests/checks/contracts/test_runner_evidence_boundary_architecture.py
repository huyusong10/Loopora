from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_runner_gatekeeper_output_normalization_has_dedicated_boundary() -> None:
    support_source = (REPO_ROOT / "src" / "loopora" / "service_runner_support.py").read_text(encoding="utf-8")
    gatekeeper_output_source = (REPO_ROOT / "src" / "loopora" / "service_runner_gatekeeper_output.py").read_text(
        encoding="utf-8"
    )
    gatekeeper_validation_source = (
        REPO_ROOT / "src" / "loopora" / "runner_gatekeeper_output_validation.py"
    ).read_text(encoding="utf-8")
    gatekeeper_evidence_gate_source = (
        REPO_ROOT / "src" / "loopora" / "runner_gatekeeper_evidence_gate.py"
    ).read_text(encoding="utf-8")
    contracts_source = design_boundary_source()

    assert "from loopora.service_runner_gatekeeper_output import ServiceRunnerGatekeeperOutputMixin" in support_source
    assert "class ServiceRunnerGatekeeperOutputMixin" in gatekeeper_output_source
    assert "from loopora.runner_gatekeeper_output_validation import coerce_gatekeeper_output" in gatekeeper_output_source
    assert "def _coerce_gatekeeper_output" in gatekeeper_output_source
    assert "def _coerce_gatekeeper_output" not in support_source
    assert "def coerce_gatekeeper_output" in gatekeeper_validation_source
    assert all(
        marker in gatekeeper_validation_source
        for marker in (
            "gatekeeper_pass_has_unmanaged_residual_risk",
            "apply_gatekeeper_evidence_gate",
            "invalid_coverage_result_refs",
        )
    )
    assert all(
        marker in gatekeeper_evidence_gate_source
        for marker in (
            "def apply_gatekeeper_evidence_gate",
            "def build_gatekeeper_evidence_context",
            "def invalid_coverage_result_refs",
        )
    )
    assert "_apply_gatekeeper_evidence_gate" not in gatekeeper_output_source
    assert "def apply_gatekeeper_evidence_gate" not in gatekeeper_validation_source
    assert "service_runner_gatekeeper_output.py" in contracts_source
    assert "runner_gatekeeper_output_validation.py" in contracts_source
    assert "runner_gatekeeper_evidence_gate.py" in contracts_source


def test_evidence_coverage_target_construction_has_dedicated_boundary() -> None:
    projection_source = (REPO_ROOT / "src" / "loopora" / "evidence_coverage.py").read_text(encoding="utf-8")
    gatekeeper_source = (REPO_ROOT / "src" / "loopora" / "evidence_coverage_gatekeeper.py").read_text(encoding="utf-8")
    target_source = (REPO_ROOT / "src" / "loopora" / "evidence_coverage_targets.py").read_text(encoding="utf-8")
    summary_source = (REPO_ROOT / "src" / "loopora" / "evidence_coverage_summary.py").read_text(encoding="utf-8")
    target_application_source = (
        REPO_ROOT / "src" / "loopora" / "evidence_coverage_target_application.py"
    ).read_text(encoding="utf-8")
    compiler_source = (REPO_ROOT / "src" / "loopora" / "compiler" / "contract_compiler.py").read_text(encoding="utf-8")
    manifest_source = (REPO_ROOT / "src" / "loopora" / "evidence_manifest.py").read_text(encoding="utf-8")
    manifest_artifacts_source = (REPO_ROOT / "src" / "loopora" / "evidence_manifest_artifacts.py").read_text(
        encoding="utf-8"
    )
    manifest_targets_source = (REPO_ROOT / "src" / "loopora" / "evidence_manifest_targets.py").read_text(
        encoding="utf-8"
    )
    run_takeaway_evidence_source = (REPO_ROOT / "src" / "loopora" / "run_takeaway_evidence.py").read_text(
        encoding="utf-8"
    )
    run_takeaway_iterations_source = (REPO_ROOT / "src" / "loopora" / "run_takeaway_iterations.py").read_text(
        encoding="utf-8"
    )
    run_takeaway_iteration_verdicts_source = (
        REPO_ROOT / "src" / "loopora" / "run_takeaway_iteration_verdicts.py"
    ).read_text(encoding="utf-8")
    contracts_source = design_boundary_source()

    for marker in ("def with_coverage_targets", "def build_coverage_targets", "def parse_target_verify_ref"):
        assert marker in target_source
        assert marker not in projection_source
    for marker in ("def latest_gatekeeper_projection", "def apply_gatekeeper_target", "def gatekeeper_has_self_measured_evidence"):
        assert marker in gatekeeper_source
        assert marker not in projection_source
    for marker in ("def summarize_evidence_coverage_projection", "def top_coverage_gaps", "def coverage_summary"):
        assert marker in summary_source
        assert marker not in projection_source
    for marker in ("def apply_target_evidence", "def coverage_result_rows", "def _target_supporting_refs"):
        assert marker in target_application_source
        assert marker not in projection_source
    assert "evidence_item_is_supporting_gatekeeper_ref" in target_application_source
    assert "evidence_item_is_supporting_gatekeeper_ref" not in projection_source
    assert "from loopora.evidence_coverage_targets import build_coverage_targets" in compiler_source
    assert "from loopora.evidence_manifest_artifacts import" in manifest_source
    assert "from loopora.evidence_manifest_targets import" in manifest_source
    for marker in ("def artifact_manifest", "def artifact_file_state", "def dedupe_artifact_refs"):
        assert marker in manifest_artifacts_source
        assert marker not in manifest_source
    for marker in ("def coverage_target_refs", "def manifest_coverage_results", "def target_index"):
        assert marker in manifest_targets_source
        assert marker not in manifest_source
    assert "from loopora.evidence_coverage_targets import parse_target_verify_ref" in manifest_targets_source
    assert "parse_target_verify_ref" not in manifest_source
    assert "from loopora.evidence_coverage_summary import summarize_evidence_coverage_projection" in run_takeaway_evidence_source
    assert "from loopora.run_takeaway_iteration_verdicts import" in run_takeaway_iterations_source
    for marker in (
        "def terminal_task_verdict_status_for_iteration",
        "def terminal_task_verdict_summary_for_iteration",
        "ACTIVE_TAKEAWAY_RUN_STATUSES",
    ):
        assert marker in run_takeaway_iteration_verdicts_source
        assert marker not in run_takeaway_iterations_source
    assert "evidence_coverage_targets.py" in contracts_source
    assert "evidence_coverage_gatekeeper.py" in contracts_source
    assert "evidence_coverage_summary.py" in contracts_source
    assert "evidence_coverage_target_application.py" in contracts_source
    assert "evidence_manifest_artifacts.py" in contracts_source
    assert "evidence_manifest_targets.py" in contracts_source
    assert "run_takeaway_iteration_verdicts.py" in contracts_source
