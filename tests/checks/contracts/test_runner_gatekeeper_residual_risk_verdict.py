from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop, _read_jsonl


def test_gatekeeper_pass_with_residual_risk_projects_task_verdict(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class ResidualRiskPassingExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "inspector":
                payload = {
                    "execution_summary": {
                        "total_checks": 2,
                        "passed": 2,
                        "failed": 0,
                        "errored": 0,
                        "total_duration_ms": 50,
                    },
                    "check_results": [
                        {
                            "id": "check_001",
                            "title": "Primary experience",
                            "status": "passed",
                            "notes": "Primary path is proven.",
                        },
                        {
                            "id": "check_002",
                            "title": "Edge path",
                            "status": "passed",
                            "notes": "Edge path is proven with a named follow-up.",
                        },
                    ],
                    "dynamic_checks": [],
                    "tester_observations": "Both required checks are covered.",
                    "coverage_results": [],
                }
            else:
                evidence_refs = [item["id"] for item in request.extra_context["step_instruction_context"]["evidence"]["items"]]
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper passed with a named acceptable follow-up risk.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [
                        {"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True},
                    ],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": evidence_refs,
                    "evidence_claims": ["The inspector evidence covers both required checks."],
                    "residual_risks": ["Manual copy polish remains a visible follow-up."],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = ResidualRiskPassingExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "inspector_step", "role_id": "inspector"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Residual Risk Gate Loop",
        max_iters=1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    ledger = _read_jsonl(run_dir / "evidence" / "ledger.jsonl")
    gatekeeper_entry = next(item for item in ledger if item["archetype"] == "gatekeeper")

    assert run["status"] == "succeeded"
    assert run["task_verdict"]["status"] == "passed_with_residual_risk"
    assert run["task_verdict"]["buckets"]["residual_risk"] == [
        {"label": "Manual copy polish remains a visible follow-up.", "managed": True}
    ]
    assert gatekeeper_entry["residual_risk"] == "Manual copy polish remains a visible follow-up."
