from __future__ import annotations

from loopora.workflows import normalize_workflow


def test_normalize_workflow_preserves_collaboration_intent() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "preset": "inspect_first",
            "collaboration_intent": "Start with evidence, then commit to one repair slice.",
            "roles": [
                {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
            ],
            "steps": [
                {"id": "inspector_step", "role_id": "inspector"},
                {"id": "builder_step", "role_id": "builder"},
            ],
        }
    )

    assert workflow["collaboration_intent"] == "Start with evidence, then commit to one repair slice."


def test_normalize_workflow_preserves_control_triggers() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                {"id": "guide", "archetype": "guide", "prompt_ref": "guide.md"},
                {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
                {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
            ],
            "controls": [
                {
                    "id": "stale_evidence_check",
                    "when": {"signal": "no_evidence_progress", "after": "20m"},
                    "call": {"role_id": "guide"},
                    "mode": "repair_guidance",
                    "max_fires_per_run": 1,
                }
            ],
        }
    )

    assert workflow["controls"] == [
        {
            "id": "stale_evidence_check",
            "when": {"signal": "no_evidence_progress", "after": "20m"},
            "call": {"role_id": "guide"},
            "mode": "repair_guidance",
            "max_fires_per_run": 1,
        }
    ]
