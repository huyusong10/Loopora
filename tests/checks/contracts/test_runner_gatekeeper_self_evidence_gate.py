from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import (
    _create_loop,
    _step_outputs_by_archetype,
)


def test_gatekeeper_pass_without_evidence_is_blocked(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class UnsupportedPassingExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype != "gatekeeper":
                raise AssertionError("Only GateKeeper should run in this fixture.")
            payload = {
                "passed": True,
                "decision_summary": "Looks good from a quick read.",
                "feedback_to_builder": "No code change is required.",
                "blocking_issues": [],
                "metrics": [],
                "failed_check_ids": [],
                "priority_failures": [],
                "composite_score": 1.0,
            }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = UnsupportedPassingExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Unsupported Gate Loop",
        max_iters=1,
        workflow={"preset": "benchmark_loop"},
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]

    assert run["status"] == "failed"
    assert gatekeeper_output["passed"] is False
    assert "gatekeeper_pass_requires_evidence_refs" in gatekeeper_output["blocking_issues"]
    assert gatekeeper_output["evidence_gate_status"] == "blocked"


def test_gatekeeper_pass_with_claims_but_no_measured_evidence_is_blocked(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class ClaimOnlyExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype != "gatekeeper":
                raise AssertionError("Only GateKeeper should run in this fixture.")
            payload = {
                "passed": True,
                "decision_summary": "Looks finished from the visible description.",
                "feedback_to_builder": "No code change is required.",
                "blocking_issues": [],
                "metrics": [],
                "failed_check_ids": [],
                "priority_failures": [],
                "composite_score": 1.0,
                "evidence_refs": ["self"],
                "evidence_claims": [
                    "The task appears complete based on a prose inspection without a measured proof path."
                ],
            }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = ClaimOnlyExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Claim Only Gate Loop",
        max_iters=1,
        workflow={"preset": "benchmark_loop"},
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]

    assert run["status"] == "failed"
    assert run["run_status"] == "failed"
    assert run["task_verdict"]["status"] == "failed"
    assert "blocking" in run["task_verdict"]["buckets"]
    assert gatekeeper_output["passed"] is False
    assert "gatekeeper_pass_requires_upstream_or_measured_evidence" in gatekeeper_output["blocking_issues"]
    assert gatekeeper_output["evidence_refs"] == ["ev_000_00_gatekeeper_step"]
