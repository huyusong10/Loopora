from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor
from loopora.run_artifacts import RunArtifactLayout

from runner_helpers import _create_loop


def test_workflow_context_does_not_promote_corrupt_stagnation_counts(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    recorded_counts: list[dict] = []

    class CountRecordingExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            recorded_counts.append(
                {
                    "covered_check_count": request.extra_context["covered_check_count"],
                    "missing_check_count": request.extra_context["missing_check_count"],
                    "consecutive_no_required_coverage_delta": request.extra_context[
                        "consecutive_no_required_coverage_delta"
                    ],
                }
            )
            if request.role_archetype == "builder":
                payload = {
                    "attempted": "Prepared a candidate.",
                    "summary": "Candidate prepared.",
                    "changed_files": [],
                }
            else:
                payload = {
                    "passed": False,
                    "decision_summary": "Not enough evidence.",
                    "feedback_to_builder": "Add proof.",
                    "blocking_issues": [],
                    "metrics": [],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 0.0,
                    "evidence_refs": [],
                    "evidence_claims": [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = CountRecordingExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Corrupt Stagnation Count Loop",
        workflow=workflow,
        max_iters=1,
    )
    queued = service.start_run(loop["id"])
    layout = RunArtifactLayout(Path(queued["runs_dir"]))
    layout.timeline_stagnation_path.write_text(
        json.dumps(
            {
                "stagnation_mode": "none",
                "evidence_progress_mode": "stalled",
                "latest_covered_check_count": "3",
                "latest_missing_check_count": True,
                "consecutive_no_required_coverage_delta": 1.5,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    run = service.execute_run(queued["id"])

    assert run["status"] == "failed"
    assert recorded_counts
    assert recorded_counts[0] == {
        "covered_check_count": 0,
        "missing_check_count": 0,
        "consecutive_no_required_coverage_delta": 0,
    }
