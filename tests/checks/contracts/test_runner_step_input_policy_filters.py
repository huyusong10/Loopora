from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop


def test_step_input_policy_filters_handoffs_and_evidence_context(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    recorded_gate_context: dict = {}

    class InputPolicyExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "builder":
                payload = {
                    "attempted": "Built a candidate.",
                    "summary": "Builder completed the candidate.",
                    "changed_files": [],
                }
            elif request.role_archetype == "inspector":
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
                            "id": request.step_id,
                            "title": request.step_id,
                            "status": "passed",
                            "notes": "Filtered evidence path.",
                        }
                    ],
                    "dynamic_checks": [],
                    "tester_observations": f"{request.step_id} evidence.",
                }
            else:
                step_instruction_context = request.extra_context["step_instruction_context"]
                recorded_gate_context.update(step_instruction_context)
                evidence_refs = [item["id"] for item in step_instruction_context["evidence"]["items"]]
                payload = {
                    "passed": True,
                    "decision_summary": "Filtered context was enough.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": evidence_refs,
                    "evidence_claims": [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = InputPolicyExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "ux", "name": "UX Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "contract", "name": "Contract Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
            {"id": "ux_step", "role_id": "ux"},
            {"id": "contract_step", "role_id": "contract"},
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "on_pass": "finish_run",
                "inputs": {
                    "handoffs_from": ["contract_step"],
                    "evidence_query": {"archetypes": ["inspector"], "limit": 1},
                },
            },
        ],
    }
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Filtered Context Loop", workflow=workflow)

    run = service.rerun(loop["id"])

    assert run["status"] == "succeeded"
    assert [item["source"]["step_id"] for item in recorded_gate_context["upstream"]["completed_steps_this_iteration"]] == ["contract_step"]
    assert [item["step_id"] for item in recorded_gate_context["evidence"]["items"]] == ["contract_step"]
    assert recorded_gate_context["evidence"]["known_ids"] == ["ev_000_02_contract_step"]
    assert recorded_gate_context["evidence"]["manifest_summary"]["claim_count"] == 1
    assert [item["id"] for item in recorded_gate_context["evidence"]["manifest_claims"]] == ["ev_000_02_contract_step"]
    assert recorded_gate_context["evidence"]["manifest_claims"][0]["verification_status"] == "run_artifact"
