from __future__ import annotations

import pytest

from loopora.workflows import WorkflowError, load_workflow_file, normalize_workflow


def _workflow_with_control(
    control: dict,
    *,
    roles: list[dict] | None = None,
    steps: list[dict] | None = None,
) -> dict:
    return {
        "version": 1,
        "roles": roles or [{"id": "guide", "archetype": "guide", "prompt_ref": "guide.md"}],
        "steps": steps or [{"id": "guide_step", "role_id": "guide"}],
        "controls": [control],
    }


@pytest.mark.parametrize(
    ("control_patch", "message", "roles", "steps"),
    [
        ({"max_fires_per_run": 0}, "control max_fires_per_run must be between 1 and 20", None, None),
        ({"max_fires_per_run": True}, "control max_fires_per_run must be an integer", None, None),
        ({"max_fires_per_run": 1.5}, "control max_fires_per_run must be an integer", None, None),
        ({"max_fires_per_run": "2"}, "control max_fires_per_run must be an integer", None, None),
        ({"mode": False}, "workflow control mode must be advisory, blocking, or repair_guidance", None, None),
        ({"when": {"signal": "no_evidence_progress", "after": False}}, r"workflow control when\.after", None, None),
        ({"when": {"signal": "cron", "after": "20m"}}, r"when\.signal", None, None),
        (
            {"id": "bad_repair", "when": {"signal": "step_failed", "after": "0s"}, "call": {"role_id": "builder"}},
            "controls may only call Inspector, Guide, or GateKeeper",
            [
                {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
            ],
            [
                {"id": "builder_step", "role_id": "builder"},
                {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
            ],
        ),
    ],
)
def test_normalize_workflow_rejects_invalid_advanced_controls(
    control_patch: dict,
    message: str,
    roles: list[dict] | None,
    steps: list[dict] | None,
) -> None:
    control = {
        "id": "advanced_control",
        "when": {"signal": "no_evidence_progress", "after": "0s"},
        "call": {"role_id": "guide"},
    }
    control.update(control_patch)

    with pytest.raises(WorkflowError, match=message):
        normalize_workflow(_workflow_with_control(control, roles=roles, steps=steps))


def test_workflow_file_can_express_controls(tmp_path) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text(
        """
        workflow:
          version: 1
          roles:
            - id: builder
              archetype: builder
              prompt_ref: builder.md
            - id: guide
              archetype: guide
              prompt_ref: guide.md
          steps:
            - id: builder_step
              role_id: builder
          controls:
            - id: stale_check
              when:
                signal: no_evidence_progress
                after: 20m
              call:
                role_id: guide
              mode: repair_guidance
        """,
        encoding="utf-8",
    )

    workflow, _prompt_files = load_workflow_file(workflow_file)
    normalized = normalize_workflow(workflow)

    assert normalized["controls"][0]["id"] == "stale_check"
    assert normalized["controls"][0]["mode"] == "repair_guidance"
