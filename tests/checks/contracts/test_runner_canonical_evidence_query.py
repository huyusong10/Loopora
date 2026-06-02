from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop


def test_evidence_query_filters_canonical_ledger_before_recent_prompt_window(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    recorded_gate_context: dict = {}
    recorded_gate_prompt = ""

    class CanonicalEvidenceQueryExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            nonlocal recorded_gate_prompt
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
                            "id": "early_inspector_evidence",
                            "title": "Early inspector evidence",
                            "status": "passed",
                            "notes": "The early inspector evidence remains the selected evidence query result.",
                        }
                    ],
                    "dynamic_checks": [],
                    "tester_observations": "Early inspector evidence.",
                    "coverage_results": [],
                }
            elif request.role_archetype == "builder":
                payload = {
                    "attempted": f"Produced filler step {request.step_id}.",
                    "summary": f"Filler step {request.step_id} completed.",
                    "changed_files": [],
                }
            else:
                step_instruction_context = request.extra_context["step_instruction_context"]
                recorded_gate_context.update(step_instruction_context)
                recorded_gate_prompt = request.prompt
                payload = {
                    "passed": False,
                    "decision_summary": "The test only inspects filtered context.",
                    "feedback_to_builder": "No follow-up required for this context projection test.",
                    "blocking_issues": ["context_projection_test"],
                    "metrics": [],
                    "metric_scores": {},
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 0.0,
                    "evidence_refs": [],
                    "evidence_claims": [],
                    "residual_risks": [],
                    "coverage_results": [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = CanonicalEvidenceQueryExecutor
    filler_steps = [{"id": f"filler_builder_{index:02d}", "role_id": "builder"} for index in range(45)]
    workflow = {
        "version": 1,
        "roles": [
            {"id": "inspector", "name": "Inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
            {"id": "builder", "name": "Builder", "archetype": "builder", "prompt_ref": "builder.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "inspector_step", "role_id": "inspector"},
            *filler_steps,
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "on_pass": "finish_run",
                "inputs": {
                    "handoffs_from": ["inspector_step"],
                    "evidence_query": {"archetypes": ["inspector"], "limit": 1},
                },
            },
        ],
    }
    loop = _create_loop(service, sample_spec_file, sample_workdir, name="Canonical Evidence Query Loop", workflow=workflow, max_iters=1)

    service.rerun(loop["id"])

    assert [item["step_id"] for item in recorded_gate_context["evidence"]["items"]] == ["inspector_step"]
    assert recorded_gate_context["evidence"]["known_ids"] == ["ev_000_00_inspector_step"]
    assert recorded_gate_context["evidence"]["manifest_summary"]["claim_count"] == 1
    assert [item["id"] for item in recorded_gate_context["evidence"]["manifest_claims"]] == ["ev_000_00_inspector_step"]
    assert 'Known ids: ["ev_000_00_inspector_step"]' in recorded_gate_prompt
    assert "gatekeeper_support=supporting" in recorded_gate_prompt
    assert "ev_000_01_filler_builder_00" not in recorded_gate_prompt
