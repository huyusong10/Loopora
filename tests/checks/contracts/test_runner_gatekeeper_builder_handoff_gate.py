from __future__ import annotations

from pathlib import Path

from compacted_contract_support import (
    BuilderHandoffOnlyExecutor,
    assert_gatekeeper_builder_ref_blocked,
    builder_claim,
    missing_proof_artifact_executor,
    run_builder_gatekeeper_handoff_case,
)


def test_gatekeeper_pass_citing_plain_builder_handoff_is_blocked(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    case = run_builder_gatekeeper_handoff_case(
        service_factory,
        sample_spec_file,
        sample_workdir,
        executor_factory=BuilderHandoffOnlyExecutor,
        name="Builder Handoff Only Loop",
    )

    assert case.run["task_verdict"]["status"] == "failed"
    assert_gatekeeper_builder_ref_blocked(case)


def test_gatekeeper_pass_citing_missing_builder_proof_artifact_is_blocked(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    proof_path = sample_workdir / "tests" / "evidence" / "proof.json"
    case = run_builder_gatekeeper_handoff_case(
        service_factory,
        sample_spec_file,
        sample_workdir,
        executor_factory=missing_proof_artifact_executor(proof_path),
        name="Missing Proof Artifact Loop",
    )

    claim = builder_claim(case)

    assert_gatekeeper_builder_ref_blocked(case)
    assert claim["verification_status"] == "run_artifact"
    assert claim["workspace_backed"] is False
    assert any(problem["code"] == "claim_artifact_missing" for problem in case.manifest["problems"])
