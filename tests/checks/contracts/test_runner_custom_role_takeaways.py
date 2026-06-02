from __future__ import annotations

import json
from pathlib import Path

from loopora.executor import CodexExecutor

from runner_helpers import _create_loop


def test_custom_role_outputs_platform_takeaway_fields(service_factory, sample_spec_file: Path, sample_workdir: Path) -> None:
    class CustomTakeawayExecutor(CodexExecutor):
        def execute(self, request, _emit_event, _should_stop, set_child_pid):
            set_child_pid(None)
            if request.role_archetype == "custom":
                payload = {
                    "status": "blocked",
                    "summary": "Custom Helper found one unresolved integration assumption.",
                    "blocking_items": ["The landing copy claims analytics-backed evidence without a matching source file."],
                    "recommended_next_action": "Either add the missing evidence source or tone down the claim before GateKeeper runs.",
                    "observations": [
                        "The current draft reads as if telemetry already exists.",
                    ],
                    "recommendations": [
                        "Tighten the claim to match the current workspace evidence.",
                    ],
                    "risks": [
                        "GateKeeper may reject unsupported claims.",
                    ],
                    "handoff_note": "Pass this to Builder before the next verification step.",
                }
            else:
                payload = {
                    "passed": False,
                    "decision_summary": "The custom helper surfaced a blocker that still needs a fix.",
                    "feedback_to_builder": "Resolve the unsupported claim first.",
                    "blocking_issues": ["unsupported_claim"],
                    "metrics": [],
                    "metric_scores": {},
                    "failed_check_ids": [],
                    "priority_failures": [],
                    "composite_score": 0.35,
                    "hard_constraint_violations": [],
                    "feedback_to_generator": "Resolve the unsupported claim first.",
                }
            request.output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return payload

    service = service_factory(scenario="success")
    service.executor_factory = CustomTakeawayExecutor
    workflow = {
        "version": 1,
        "roles": [
            {"id": "custom_helper", "name": "Custom Helper", "archetype": "custom", "prompt_ref": "custom.md"},
            {"id": "gatekeeper", "name": "GateKeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
        ],
        "steps": [
            {"id": "custom_step", "role_id": "custom_helper"},
            {"id": "gatekeeper_step", "role_id": "gatekeeper"},
        ],
    }
    loop = _create_loop(
        service,
        sample_spec_file,
        sample_workdir,
        name="Custom Takeaway Loop",
        workflow=workflow,
        completion_mode="rounds",
        max_iters=1,
    )

    run = service.rerun(loop["id"])
    custom_handoff = json.loads(
        (Path(run["runs_dir"]) / "iterations" / "iter_000" / "steps" / "00__custom_step" / "handoff.json").read_text(
            encoding="utf-8"
        )
    )

    assert custom_handoff["status"] == "blocked"
    assert custom_handoff["summary"] == "Custom Helper found one unresolved integration assumption."
    assert custom_handoff["blocking_items"] == ["The landing copy claims analytics-backed evidence without a matching source file."]
    assert custom_handoff["recommended_next_action"] == ("Either add the missing evidence source or tone down the claim before GateKeeper runs.")
