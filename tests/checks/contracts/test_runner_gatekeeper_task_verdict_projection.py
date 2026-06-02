from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor
from loopora.run_takeaways import build_run_key_takeaways

from runner_helpers import (
    _create_loop,
    _step_outputs_by_archetype,
)


def test_gatekeeper_pass_with_uncovered_required_targets_does_not_pass_task_verdict(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class UncoveredRequiredTargetsExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "builder":
                payload = {
                    "attempted": "Left a generic implementation handoff.",
                    "abandoned": "",
                    "assumption": "",
                    "summary": "No required coverage target was directly verified.",
                    "changed_files": [],
                }
            elif request.role_archetype == "inspector":
                payload = {
                    "execution_summary": {
                        "total_checks": 0,
                        "passed": 0,
                        "failed": 0,
                        "errored": 0,
                        "total_duration_ms": 1,
                    },
                    "check_results": [],
                    "dynamic_checks": [],
                    "tester_observations": "This produced an upstream observation without verifying required targets.",
                    "coverage_results": [],
                }
            else:
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper accepted a generic upstream observation.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [
                        {"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True},
                    ],
                    "metric_scores": {
                        "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
                    },
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": ["ev_000_01_inspector_step"],
                    "evidence_claims": ["The inspector produced an observation, but no required target was verified."],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = UncoveredRequiredTargetsExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Uncovered Required Target Loop",
        max_iters=1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    coverage = json.loads((run_dir / "evidence" / "coverage.json").read_text(encoding="utf-8"))
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]
    latest_iteration_summary = json.loads(
        (run_dir / "context" / "latest_iteration_summary.json").read_text(encoding="utf-8")
    )
    takeaways = build_run_key_takeaways(service.get_run(run["id"]))
    latest_takeaway = takeaways["iterations"][0]

    assert run["status"] == "succeeded"
    assert gatekeeper_output["evidence_gate_status"] == "passed"
    assert "Task verdict passes" not in gatekeeper_output["decision_summary"]
    assert "Loopora Core still derives the task verdict" in gatekeeper_output["decision_summary"]
    assert "Task verdict passes" not in latest_iteration_summary["gatekeeper_verdict"]["decision_summary"]
    assert coverage["status"] == "partial"
    assert run["task_verdict"]["status"] == "insufficient_evidence"
    assert run["task_verdict"]["source"] == "gatekeeper"
    assert latest_takeaway["status"] == "blocked"
    assert "Task verdict insufficient evidence" in latest_takeaway["summary"]
    assert "Required coverage targets still lack direct evidence" in latest_takeaway["summary"]
    events = service.stream_events(run["id"], limit=200)
    assert any(
        event["event_type"] == "run_finished"
        and event["payload"]["status"] == "succeeded"
        and event["payload"]["task_verdict_status"] == "insufficient_evidence"
        and event["payload"]["task_verdict_source"] == "gatekeeper"
        and event["payload"]["task_verdict_summary"] == run["task_verdict"]["summary"]
        for event in events
    )
