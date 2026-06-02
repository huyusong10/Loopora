from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from loopora.run_takeaways import empty_judgment_contract
from run_takeaway_projection_service_test_support import (
    rerun_takeaway_loop,
    takeaway_client,
)

from web_api_test_support import _assert_key_takeaway_judgment_contract


EXPECTED_TAKEAWAY_COVERED_CHECK_COUNT = 2
EXPECTED_TAKEAWAY_REQUIRED_CHECK_COUNT = 2
MIN_TAKEAWAY_ROLE_CONCLUSION_COUNT = 2
MIN_TAKEAWAY_TARGET_COUNT = 5


def test_api_run_key_takeaways_returns_iteration_role_conclusions(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = rerun_takeaway_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Takeaway Loop",
    )

    client = takeaway_client(service)
    response = client.get(f"/api/runs/{run['id']}/key-takeaways")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["build_dir"] == str(sample_workdir.resolve())
    assert payload["log_dir"].endswith(f"/.loopora/runs/{run['id']}")
    assert payload["run_status"] == "succeeded"
    assert payload["task_verdict"]["status"] == "passed"
    assert payload["task_verdict"]["source"] == "gatekeeper"
    assert payload["task_verdict_path"] == "evidence/task_verdict.json"
    _assert_key_takeaway_judgment_contract(payload["judgment_contract"])
    assert set(payload["evidence_buckets"]) == {"proven", "weak", "unproven", "blocking", "residual_risk"}
    assert payload["iteration_count"] >= 1
    assert payload["role_conclusion_count"] >= MIN_TAKEAWAY_ROLE_CONCLUSION_COUNT
    latest_iteration = payload["iterations"][0]
    assert latest_iteration["display_iter"] >= 1
    assert latest_iteration["summary"]
    role_names = {item["role_name"] for item in latest_iteration["roles"]}
    assert "Builder" in role_names
    assert "GateKeeper" in role_names
    gatekeeper = next(item for item in latest_iteration["roles"] if item["role_name"] == "GateKeeper")
    assert gatekeeper["composite_score"] is not None
    coverage = payload["evidence_coverage"]
    assert coverage["ledger_path"] == "evidence/ledger.jsonl"
    assert coverage["coverage_path"] == "evidence/coverage.json"
    assert coverage["evidence_count"] == payload["evidence_count"]
    assert coverage["status"] == "weak"
    assert coverage["summary"]["reason"]
    assert coverage["check_count"] == EXPECTED_TAKEAWAY_REQUIRED_CHECK_COUNT
    assert coverage["covered_check_count"] == EXPECTED_TAKEAWAY_COVERED_CHECK_COUNT
    assert coverage["missing_check_count"] == 0
    assert set(coverage["covered_check_ids"]) == {"check_001", "check_002"}
    assert coverage["target_count"] >= MIN_TAKEAWAY_TARGET_COUNT
    assert coverage["missing_target_count"] >= 1
    assert coverage["top_gaps"]
    assert coverage["latest_gatekeeper"]["evidence_refs"]
    assert coverage["evidence_kind_counts"]["inspection"] >= 1
    assert coverage["evidence_kind_counts"]["verdict"] >= 1
    manifest = payload["evidence_manifest"]
    assert manifest["manifest_path"] == "evidence/manifest.json"
    assert manifest["claim_count"] == payload["evidence_count"]
    assert manifest["artifact_backed_claim_count"] == manifest["claim_count"]
    assert manifest["run_artifact_claim_count"] >= 1
    assert set(manifest) >= {
        "direct_proof_claim_count",
        "workspace_artifact_claim_count",
        "ledger_only_claim_count",
        "unverified_claim_count",
        "problem_count",
    }


def test_api_run_key_takeaways_tolerates_invalid_utf8_json_artifacts(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    run = rerun_takeaway_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Corrupt Artifact Takeaway Loop",
    )
    run_dir = Path(run["runs_dir"])
    (run_dir / "contract" / "compiled_spec.json").write_bytes(b"\xff")
    (run_dir / "contract" / "run_contract.json").write_bytes(b"\xff")
    (run_dir / "evidence" / "ledger.jsonl").write_bytes(b"\xff")
    for handoff_path in run_dir.glob("iterations/iter_*/steps/*/handoff.json"):
        handoff_path.write_bytes(b"\xff")
        break

    client = takeaway_client(service)
    response = client.get(f"/api/runs/{run['id']}/key-takeaways")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["evidence_count"] == 0
    assert payload["run_status"] == "succeeded"
    assert payload["judgment_contract"] == empty_judgment_contract()
