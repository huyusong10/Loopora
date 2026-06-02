from __future__ import annotations

from pathlib import Path

from compacted_contract_support import (
    ADVISORY_VERIFY_REFS,
    GatekeeperAdvisoryCoverageExecutor,
    assert_advisory_targets_covered,
    gatekeeper_entry,
    inspector_advisory_coverage_executor,
    inspector_gatekeeper_workflow,
    run_advisory_coverage_loop,
)


def test_coverage_results_cover_advisory_targets(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    case = run_advisory_coverage_loop(
        (service_factory, sample_spec_file, sample_workdir),
        name="Coverage Target Loop",
        executor_factory=inspector_advisory_coverage_executor,
    )

    assert_advisory_targets_covered(case)
    for verify_ref in ADVISORY_VERIFY_REFS:
        assert any(verify_ref in entry["verifies"] for entry in case.evidence_ledger)


def test_gatekeeper_coverage_results_cover_advisory_targets(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    case = run_advisory_coverage_loop(
        (service_factory, sample_spec_file, sample_workdir),
        name="GateKeeper Coverage Target Loop",
        executor_factory=GatekeeperAdvisoryCoverageExecutor,
        workflow=inspector_gatekeeper_workflow(),
    )
    entry = gatekeeper_entry(case)

    assert_advisory_targets_covered(case)
    for verify_ref in ADVISORY_VERIFY_REFS:
        assert verify_ref in entry["verifies"]
    assert {item["target_id"] for item in entry["coverage_results"]} >= {
        "success_surface.surface_001",
        "fake_done.risk_001",
        "evidence_preference.pref_001",
    }
    related_refs = set(entry["related_evidence_ids"])
    assert all(item["evidence_refs"] for item in entry["coverage_results"])
    assert all(set(item["evidence_refs"]) <= related_refs for item in entry["coverage_results"])
