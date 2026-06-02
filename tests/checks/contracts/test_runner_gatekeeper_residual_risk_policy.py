from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop, _step_outputs_by_archetype


def test_loop_rejects_gatekeeper_residual_risk_when_contract_disallows_acceptance(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    class DisallowedResidualRiskExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "inspector":
                payload = {
                    "execution_summary": {
                        "total_checks": 1,
                        "passed": 1,
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
                    ],
                    "dynamic_checks": [],
                    "tester_observations": "The required check is covered.",
                    "coverage_results": [],
                }
            else:
                evidence_refs = [item["id"] for item in request.extra_context["step_instruction_context"]["evidence"]["items"]]
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper accepted a managed residual risk.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [
                        {"name": "quality_score", "value": 1.0, "threshold": 0.9, "passed": True},
                    ],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": evidence_refs,
                    "evidence_claims": ["The inspector evidence covers the required check."],
                    "residual_risks": ["Manual billing export remains visible as a follow-up owned by Support."],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = DisallowedResidualRiskExecutor
    spec_file = sample_spec_file.with_name("no_residual_risk_spec.md")
    spec_file.write_text(
        sample_spec_file.read_text(encoding="utf-8").replace(
            "Minor copy polish can wait, but unverifiable completion should fail closed.",
            "No residual risk is acceptable; any remaining risk must fail closed.",
        ),
        encoding="utf-8",
    )
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
        spec_file,
        sample_workdir,
        name="No Residual Risk Gate Loop",
        max_iters=1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]

    assert run["status"] == "failed"
    assert run["task_verdict"]["status"] == "failed"
    assert gatekeeper_output["passed"] is False
    assert gatekeeper_output["blocking_issues"][0].startswith("gatekeeper_pass_violates_no_residual_risk_policy:")
    assert "Manual billing export remains visible as a follow-up owned by Support." in gatekeeper_output["blocking_issues"][0]
    assert gatekeeper_output["residual_risks"] == ["Manual billing export remains visible as a follow-up owned by Support."]
