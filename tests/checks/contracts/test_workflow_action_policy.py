from __future__ import annotations

import pytest

from loopora.workflows import (
    WorkflowError,
    default_role_execution_settings,
    default_step_action_policy,
    normalize_workflow,
)


def test_normalize_workflow_adds_default_step_action_policies() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                {"id": "inspector", "archetype": "inspector", "prompt_ref": "inspector.md"},
                {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
                {"id": "guide", "archetype": "guide", "prompt_ref": "guide.md"},
                {"id": "custom", "archetype": "custom", "prompt_ref": "custom.md"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
                {"id": "inspector_step", "role_id": "inspector"},
                {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "finish_run"},
                {"id": "guide_step", "role_id": "guide"},
                {"id": "custom_step", "role_id": "custom"},
            ],
        }
    )

    policies = {step["id"]: step["action_policy"] for step in workflow["steps"]}
    assert policies["builder_step"] == {
        "workspace": "workspace_write",
        "can_block": False,
        "can_finish_run": False,
    }
    assert policies["inspector_step"] == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": False,
    }
    assert policies["gatekeeper_step"] == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": True,
    }
    assert policies["guide_step"] == {
        "workspace": "read_only",
        "can_block": False,
        "can_finish_run": False,
    }
    assert policies["custom_step"] == {
        "workspace": "read_only",
        "can_block": False,
        "can_finish_run": False,
    }


def test_default_gatekeeper_action_policy_only_finishes_when_step_finishes_run() -> None:
    assert default_step_action_policy(archetype="gatekeeper", on_pass="continue") == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": False,
    }
    assert default_step_action_policy(archetype="gatekeeper", on_pass="finish_run")["can_finish_run"] is True


def test_normalize_workflow_materializes_execution_defaults_when_role_only_overrides_model() -> None:
    workflow = normalize_workflow(
        {
            "version": 1,
            "roles": [
                {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md", "model": "gpt-5.4-mini"},
            ],
            "steps": [
                {"id": "builder_step", "role_id": "builder"},
            ],
        }
    )

    builder = workflow["roles"][0]
    defaults = default_role_execution_settings()

    assert builder["model"] == "gpt-5.4-mini"
    assert builder["executor_kind"] == defaults["executor_kind"]
    assert builder["executor_mode"] == defaults["executor_mode"]
    assert builder["command_cli"] == defaults["command_cli"]
    assert builder["reasoning_effort"] == defaults["reasoning_effort"]


def test_normalize_workflow_rejects_finish_run_for_non_gatekeeper_steps() -> None:
    with pytest.raises(WorkflowError, match="non-gatekeeper steps only support on_pass=continue"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
                ],
                "steps": [
                    {"id": "builder_step", "role_id": "builder", "on_pass": "finish_run"},
                ],
            }
        )


def test_normalize_workflow_rejects_invalid_gatekeeper_on_pass_values() -> None:
    with pytest.raises(WorkflowError, match="gatekeeper step on_pass must be continue or finish_run"):
        normalize_workflow(
            {
                "version": 1,
                "roles": [
                    {"id": "gatekeeper", "archetype": "gatekeeper", "prompt_ref": "gatekeeper.md"},
                ],
                "steps": [
                    {"id": "gatekeeper_step", "role_id": "gatekeeper", "on_pass": "halt"},
                ],
            }
        )
