from __future__ import annotations

from loopora.agent_native_step_view_paths import (
    agent_native_step_contract_path_text,
    agent_native_step_view_artifact_path_texts,
    agent_native_step_view_path_text,
)


def test_agent_native_step_view_paths_prefer_split_contract_fields() -> None:
    step_view = {
        "agent_step_view_path": "steps/agent_step_view.json",
        "agent_step_view_absolute_path": "/runs/steps/agent_step_view.json",
        "step_contract_path": "steps/step_contract.json",
        "step_contract_absolute_path": "/runs/steps/step_contract.json",
    }

    assert agent_native_step_view_path_text(step_view) == "steps/agent_step_view.json"
    assert agent_native_step_view_path_text(step_view, absolute=True) == "/runs/steps/agent_step_view.json"
    assert agent_native_step_contract_path_text(step_view) == "steps/step_contract.json"
    assert agent_native_step_contract_path_text(step_view, absolute=True) == "/runs/steps/step_contract.json"


def test_agent_native_step_view_paths_do_not_fallback_to_legacy_capsule_fields() -> None:
    step_view = {"capsule_path": "steps/capsule.json", "capsule_absolute_path": "/runs/steps/capsule.json"}

    assert agent_native_step_view_path_text(step_view) == ""
    assert agent_native_step_contract_path_text(step_view) == ""
    assert agent_native_step_contract_path_text(step_view, absolute=True) == ""


def test_agent_native_step_view_artifact_paths_are_unique_and_write_split_paths_first() -> None:
    step_view = {
        "agent_step_view_absolute_path": "/runs/steps/agent_step_view.json",
        "agent_step_view_path": "steps/agent_step_view.json",
        "step_contract_absolute_path": "/runs/steps/step_contract.json",
    }

    assert agent_native_step_view_artifact_path_texts(step_view) == [
        "/runs/steps/agent_step_view.json",
        "/runs/steps/step_contract.json",
    ]
