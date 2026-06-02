from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop, _read_jsonl, _step_outputs_by_archetype


def test_benchmark_loop_can_finish_before_builder_runs(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class BenchmarkPassingExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "gatekeeper":
                payload = {
                    "passed": True,
                    "decision_summary": "Benchmark target already satisfied.",
                    "feedback_to_builder": "No code change is required.",
                    "blocking_issues": [],
                    "metrics": [],
                    "metric_scores": {
                        "check_pass_rate": {"value": 1.0, "threshold": 1.0, "passed": True},
                        "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
                    },
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": [],
                    "evidence_claims": [
                        "The benchmark fixture is already satisfied by the existing project-owned proof output."
                    ],
                }
                request.output_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                return payload
            raise AssertionError("Builder should not run when benchmark loop already passes.")

    service = service_factory(scenario="success")
    service.executor_factory = BenchmarkPassingExecutor
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Benchmark Loop",
        workflow={"preset": "benchmark_loop"},
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    step_outputs = _step_outputs_by_archetype(run_dir)
    coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
    ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    targets = {target["id"]: target for target in coverage["targets"]}
    gatekeeper_entry = next(item for item in ledger if item["archetype"] == "gatekeeper")

    assert run["status"] == "succeeded"
    assert "builder" not in step_outputs
    assert step_outputs["gatekeeper"][-1]["output"]["passed"] is True
    assert gatekeeper_entry["measured_evidence"] is True
    assert gatekeeper_entry["concrete_evidence_claim_count"] == 1
    assert coverage["latest_gatekeeper"]["self_measured_evidence"] is True
    assert targets["gatekeeper.finish"]["status"] == "covered"
