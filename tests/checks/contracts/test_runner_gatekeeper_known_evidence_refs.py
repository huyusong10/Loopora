from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop, _step_outputs_by_archetype


KNOWN_EVIDENCE_REF_PASS_ITERATION = 21


def test_gatekeeper_validates_older_known_evidence_ref_from_canonical_ledger(
    service_factory,
    sample_spec_file: Path,
    sample_workdir: Path,
) -> None:
    target_ref = "ev_000_00_inspector_step"

    class OlderEvidenceRefExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            iter_id = int(request.extra_context.get("iter_id") or 0)
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
                            "notes": "The first run already proved the primary experience.",
                        },
                        {
                            "id": "check_002",
                            "title": "Edge path",
                            "status": "passed",
                            "notes": "The first run already proved the edge path.",
                        },
                    ],
                    "dynamic_checks": [],
                    "tester_observations": f"Inspector evidence for iteration {iter_id}.",
                    "coverage_results": [],
                }
            else:
                passed = iter_id >= KNOWN_EVIDENCE_REF_PASS_ITERATION
                payload = {
                    "passed": passed,
                    "decision_summary": "Older inspector evidence remains valid." if passed else "Keep accumulating iterations.",
                    "feedback_to_builder": "",
                    "blocking_issues": [],
                    "metrics": [
                        {"name": "quality_score", "value": 1.0 if passed else 0.4, "threshold": 0.9, "passed": passed},
                    ],
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 1.0 if passed else 0.4,
                    "evidence_refs": [target_ref] if passed else [],
                    "evidence_claims": ["The older inspector evidence id was cited after it fell out of the prompt item summary."] if passed else [],
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = OlderEvidenceRefExecutor
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
        name="Older Evidence Ref Loop",
        max_iters=KNOWN_EVIDENCE_REF_PASS_ITERATION + 1,
        workflow=workflow,
    )

    run = service.rerun(loop["id"])
    run_dir = Path(run["runs_dir"])
    gatekeeper_output = _step_outputs_by_archetype(run_dir)["gatekeeper"][-1]["output"]
    final_context = json.loads((run_dir / "iterations" / f"iter_{KNOWN_EVIDENCE_REF_PASS_ITERATION:03d}" / "steps" / "01__gatekeeper_step" / "step_instruction_context.json").read_text(encoding="utf-8"))

    assert target_ref in final_context["evidence"]["known_ids"]
    assert target_ref not in {item["id"] for item in final_context["evidence"]["items"]}
    assert run["status"] == "succeeded"
    assert gatekeeper_output["passed"] is True
    assert gatekeeper_output["evidence_gate_status"] == "passed"
    assert gatekeeper_output["evidence_refs"] == [target_ref]
