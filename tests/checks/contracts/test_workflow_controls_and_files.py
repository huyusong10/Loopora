from __future__ import annotations

import pytest

from loopora.workflows import (
    WorkflowError,
    load_prompt_file,
    load_workflow_file,
    normalize_workflow,
    resolve_prompt_files,
)


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


def test_workflow_file_reports_encoding_and_parse_errors(tmp_path) -> None:
    invalid_utf8_file = tmp_path / "workflow.yml"
    invalid_utf8_file.write_bytes(b"\xff")
    with pytest.raises(WorkflowError, match="UTF-8 encoded YAML or JSON"):
        load_workflow_file(invalid_utf8_file)

    invalid_yaml_file = tmp_path / "workflow.yaml"
    invalid_yaml_file.write_text("workflow:\n  roles: [", encoding="utf-8")
    with pytest.raises(WorkflowError, match="invalid workflow YAML"):
        load_workflow_file(invalid_yaml_file)

    invalid_json_file = tmp_path / "workflow.json"
    invalid_json_file.write_text("{", encoding="utf-8")
    with pytest.raises(WorkflowError, match="invalid workflow JSON"):
        load_workflow_file(invalid_json_file)


def test_workflow_file_rejects_non_object_nested_workflow(tmp_path) -> None:
    workflow_file = tmp_path / "workflow.yml"
    workflow_file.write_text("workflow:\n  - not\n  - an\n  - object\n", encoding="utf-8")

    with pytest.raises(WorkflowError, match="workflow file workflow must be an object"):
        load_workflow_file(workflow_file)


def test_prompt_file_reports_encoding_errors(tmp_path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_bytes(b"\xff")

    with pytest.raises(WorkflowError, match="UTF-8 encoded Markdown"):
        load_prompt_file(prompt_file)


def test_prompt_file_reports_read_errors(tmp_path) -> None:
    prompt_file = tmp_path / "missing.md"

    with pytest.raises(WorkflowError, match="could not be read"):
        load_prompt_file(prompt_file)


def test_normalize_workflow_rejects_write_roles_inside_parallel_groups() -> None:
    with pytest.raises(WorkflowError, match="parallel_group steps must be read-only"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "builder_a", "archetype": "builder", "prompt_ref": "builder.md"},
                    {"id": "builder_b", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_a_step", "role_id": "builder_a", "parallel_group": "builders"},
                    {"id": "builder_b_step", "role_id": "builder_b", "parallel_group": "builders"},
                ],
            }
        )


def test_normalize_workflow_rejects_non_builder_workspace_write() -> None:
    with pytest.raises(WorkflowError, match=r"only Builder steps may set action_policy\.workspace=workspace_write"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                ],
                "steps": [
                    {
                        "id": "inspector_step",
                        "role_id": "inspector",
                        "action_policy": {"workspace": "workspace_write"},
                    },
                ],
            }
        )


def test_normalize_workflow_rejects_non_string_action_policy_workspace() -> None:
    with pytest.raises(WorkflowError, match=r"workflow step action_policy\.workspace must be read_only or workspace_write"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {
                        "id": "builder_step",
                        "role_id": "builder",
                        "action_policy": {"workspace": False},
                    },
                ],
            }
        )


def test_normalize_workflow_rejects_non_gatekeeper_finish_permission() -> None:
    with pytest.raises(WorkflowError, match=r"only GateKeeper steps may set action_policy\.can_finish_run=true"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {
                        "id": "builder_step",
                        "role_id": "builder",
                        "action_policy": {
                            "workspace": "workspace_write",
                            "can_finish_run": True,
                        },
                    },
                ],
            }
        )


def test_normalize_workflow_rejects_parallel_finish_permissions() -> None:
    with pytest.raises(WorkflowError, match="parallel_group steps may not finish runs"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
                    {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                ],
                "steps": [
                    {
                        "id": "gatekeeper_step",
                        "role_id": "gatekeeper",
                        "on_pass": "finish_run",
                        "parallel_group": "review_pack",
                    },
                    {"id": "inspector_step", "role_id": "inspector", "parallel_group": "review_pack"},
                ],
            }
        )


def test_normalize_workflow_requires_parallel_group_steps_to_be_contiguous() -> None:
    with pytest.raises(WorkflowError, match="parallel_group steps must be contiguous"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "inspector_a", "archetype": "inspector", "prompt_ref": "inspector.md"},
                    {"id": "inspector_b", "archetype": "inspector", "prompt_ref": "inspector.md"},
                    {"id": "inspector_c", "archetype": "inspector", "prompt_ref": "inspector.md"},
                ],
                "steps": [
                    {"id": "a", "role_id": "inspector_a", "parallel_group": "pack"},
                    {"id": "b", "role_id": "inspector_b", "parallel_group": "other"},
                    {"id": "c", "role_id": "inspector_c", "parallel_group": "pack"},
                ],
            }
        )


def test_normalize_workflow_rejects_unknown_input_policy_keys() -> None:
    with pytest.raises(WorkflowError, match="workflow step inputs contains unknown keys"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                ],
                "steps": [
                    {"id": "inspector_step", "role_id": "inspector", "inputs": {"hidden_context": True}},
                ],
            }
        )


def test_resolve_prompt_files_drops_unused_entries() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "custom-builder.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
            ],
        }
    )

    resolved = resolve_prompt_files(
        workflow,
        {
            "custom-builder.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
            "unused.md": """---
version: 1
archetype: inspector
---

This prompt should be dropped.
""",
        },
    )

    assert resolved == {
        "custom-builder.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
    }


def test_resolve_prompt_files_rejects_invalid_prompt_file_keys() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
            ],
        }
    )

    with pytest.raises(WorkflowError, match="prompt_ref must be a safe relative path"):
        resolve_prompt_files(
            workflow,
            {
                "../escape.md": """---
version: 1
archetype: builder
---

This key should be rejected instead of silently dropped.
""",
            },
        )


def test_resolve_prompt_files_rejects_shared_prompt_ref_with_mismatched_archetype() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "shared.md"},
                {"id": "inspector", "archetype": "inspector", "prompt_ref": "shared.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
                {"id": "inspector_step", "role_id": "inspector"},
            ],
        }
    )

    with pytest.raises(
        WorkflowError,
        match="prompt archetype builder does not match expected archetype inspector",
    ):
        resolve_prompt_files(
            workflow,
            {
                "shared.md": """---
version: 1
archetype: builder
---

Keep the builder prompt stable.
""",
            },
        )
