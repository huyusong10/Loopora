from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop, _read_jsonl


def test_round_mode_carries_gatekeeper_residual_risk_into_next_iteration_prompt(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    second_builder_prompt = ""
    second_builder_context: dict = {}

    class ResidualRiskCarryForwardExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            nonlocal second_builder_prompt, second_builder_context
            set_child_pid(None)
            iter_id = request.extra_context["iter_id"]
            if request.role_archetype == "builder":
                if iter_id == 1:
                    second_builder_prompt = request.prompt
                    second_builder_context = request.extra_context["step_instruction_context"]
                payload = {
                    "attempted": "Built the primary slice.",
                    "summary": "Builder changed only the focused primary slice.",
                    "changed_files": [],
                    "proof_files": [],
                    "proof_artifacts": [],
                    "artifact_paths": [],
                }
            elif request.role_archetype == "inspector":
                payload = {
                    "execution_summary": {
                        "total_checks": 1,
                        "passed": 1,
                        "failed": 0,
                        "errored": 0,
                        "total_duration_ms": 20,
                    },
                    "check_results": [
                        {
                            "id": "primary_slice_check",
                            "title": "Primary slice check",
                            "status": "passed",
                            "notes": "Inspector produced direct evidence for the primary slice.",
                        }
                    ],
                    "dynamic_checks": [],
                    "tester_observations": "Inspector evidence covers the primary slice.",
                    "coverage_results": [],
                }
            else:
                step_instruction_context = request.extra_context["step_instruction_context"]
                evidence_refs = [item["id"] for item in step_instruction_context["evidence"]["items"] if item.get("archetype") == "inspector"]
                payload = {
                    "passed": True,
                    "decision_summary": "GateKeeper passed with a managed residual risk in round mode.",
                    "feedback_to_builder": "Keep the named residual risk visible while continuing the next round.",
                    "blocking_issues": [],
                    "hard_constraint_violations": [],
                    "metrics": [],
                    "metric_scores": {
                        "check_pass_rate": {"value": 1.0, "threshold": 0.9, "passed": True},
                        "quality_score": {"value": 1.0, "threshold": 0.9, "passed": True},
                    },
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0,
                    "evidence_refs": evidence_refs,
                    "evidence_claims": ["Inspector proof covers the primary slice."],
                    "residual_risks": ["Manual copy polish remains visible as a follow-up owned by docs."],
                    "coverage_results": [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = ResidualRiskCarryForwardExecutor
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
            {"id": "gatekeeper_step", "role_id": "gatekeeper"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Residual Risk Carry Forward Loop",
        workflow=workflow,
        completion_mode="rounds",
        max_iters=2,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    first_iteration_summary = json.loads((run_dir / "iterations" / "iter_000" / "summary.json").read_text(encoding="utf-8"))
    role_requests = _read_jsonl(run_dir / "context" / "role_requests.jsonl")
    second_builder_request = next(item for item in role_requests if item["role_archetype"] == "builder" and item["iter"] == 1)

    assert second_builder_prompt
    assert first_iteration_summary["gatekeeper_verdict"]["residual_risks"] == [
        "Manual copy polish remains visible as a follow-up owned by docs."
    ]
    assert second_builder_context["upstream"]["previous_iteration_summary"]["gatekeeper_verdict"]["residual_risks"] == [
        "Manual copy polish remains visible as a follow-up owned by docs."
    ]
    assert 'GateKeeper residual risks: ["Manual copy polish remains visible as a follow-up owned by docs."]' in second_builder_prompt
    assert "residual_risk=Manual copy polish remains visible as a follow-up owned by docs." in second_builder_prompt
    assert second_builder_request["context_summary"]["previous_iteration_summary"]["gatekeeper_residual_risk_count"] == 1
