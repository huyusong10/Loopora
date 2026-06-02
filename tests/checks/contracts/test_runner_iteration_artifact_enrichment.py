from __future__ import annotations

import json
from pathlib import Path

from runner_helpers import (
    _create_loop,
    _read_jsonl,
    _step_outputs_by_archetype,
)


def test_successful_run_enriches_logs_and_role_outputs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Verbose Logs Loop")

    run = service.rerun(loop["id"])

    run_dir = Path(run["runs_dir"])
    step_outputs = _step_outputs_by_archetype(run_dir)
    builder_output = step_outputs["builder"][-1]["output"]
    tester_output = step_outputs["inspector"][-1]["output"]
    verifier_verdict = step_outputs["gatekeeper"][-1]["output"]
    metrics_history = _read_jsonl(run_dir / "timeline" / "metrics.jsonl")
    evidence_ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    iteration_log = _read_jsonl(run_dir / "iteration_log.jsonl")
    latest_iteration_summary = json.loads(
        (run_dir / "context" / "latest_iteration_summary.json").read_text(encoding="utf-8")
    )

    assert "frozen task contract" in builder_output["attempted"]
    assert "proof surface" in builder_output["summary"]
    assert tester_output["status_counts"]["overall"]["passed"] >= 1
    assert "failed_items" in tester_output
    assert "frozen run contract" in tester_output["tester_observations"]
    assert "Blocking or Unproven" in tester_output["tester_observations"]
    assert verifier_verdict["decision_summary"]
    assert "task verdict" in verifier_verdict["decision_summary"]
    assert "coverage targets" in verifier_verdict["decision_summary"]
    assert "run artifacts" in verifier_verdict["decision_summary"]
    assert verifier_verdict["evidence_refs"]
    assert verifier_verdict["evidence_claims"]
    assert "Proven:" in verifier_verdict["evidence_claims"][0]
    assert "run status separate from task verdict" in verifier_verdict["evidence_claims"][0]
    assert verifier_verdict["evidence_gate_status"] == "passed"
    assert "failing_metrics" in verifier_verdict
    assert "next_actions" in verifier_verdict
    assert metrics_history[-1]["stagnation_mode"] in {"none", "plateau", "regression"}
    assert "score_delta" in metrics_history[-1]
    assert metrics_history[-1]["evidence_refs"] == verifier_verdict["evidence_refs"]
    assert evidence_ledger
    assert {entry["archetype"] for entry in evidence_ledger} >= {"inspector", "gatekeeper"}
    assert {entry["evidence_kind"] for entry in evidence_ledger} >= {"inspection", "verdict"}
    assert step_outputs["inspector"][-1]["metadata"]["archetype"] == "inspector"

    complete_entries = [entry for entry in iteration_log if entry["phase"] == "complete"]
    assert complete_entries
    latest_entry = complete_entries[-1]
    assert latest_entry["generator"]["changed_files"] == []
    assert latest_entry["tester"]["status_counts"]["overall"]["passed"] >= 1
    assert latest_entry["verifier"]["decision_summary"]
    assert latest_entry["score"]["composite"] == verifier_verdict["composite_score"]
    assert latest_iteration_summary["score"]["composite"] == verifier_verdict["composite_score"]
    assert latest_iteration_summary["step_handoffs"]
    assert all(handoff["evidence_refs"] for handoff in latest_iteration_summary["step_handoffs"])
    assert all("parallel_group" in item for item in latest_iteration_summary["workflow"])
