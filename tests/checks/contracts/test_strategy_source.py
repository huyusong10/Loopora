from __future__ import annotations

import pytest

from loopora import strategy_source
from loopora import workflows


def test_strategy_source_preset_copy_preserves_legacy_workflow_copy_contract() -> None:
    assert strategy_source.strategy_source_preset_copy("quality_gate") == workflows.workflow_preset_copy("quality_gate")


def test_strategy_source_constants_preserve_legacy_workflow_constant_contract() -> None:
    assert strategy_source.StrategySourceError is workflows.WorkflowError
    assert strategy_source.DEFAULT_STRATEGY_SOURCE_PRESET == workflows.DEFAULT_WORKFLOW_PRESET
    assert strategy_source.STRATEGY_SOURCE_ARCHETYPES == workflows.ARCHETYPES
    assert strategy_source.LEGACY_STRATEGY_ROLE_BY_ARCHETYPE == workflows.LEGACY_ROLE_BY_ARCHETYPE
    assert strategy_source.STRATEGY_PROMPT_FILES == workflows.PROMPT_FILES
    assert strategy_source.STRATEGY_ROLE_EXECUTION_FIELDS == workflows.ROLE_EXECUTION_FIELDS
    assert strategy_source.STRATEGY_ROLE_POSTURE_FIELDS == workflows.ROLE_POSTURE_FIELDS


def test_strategy_source_helpers_preserve_legacy_workflow_helper_contract() -> None:
    source = {
        "version": 1,
        "roles": [
            {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
        ],
    }

    assert strategy_source.normalize_strategy_source_identifier(
        "builder_step",
        field_name="step id",
    ) == workflows.normalize_workflow_identifier(
        "builder_step",
        field_name="step id",
    )
    assert strategy_source.normalize_strategy_source_version(None) == workflows.normalize_workflow_version(None)
    assert strategy_source.strategy_source_warnings(source) == workflows.workflow_warnings(source)
    assert strategy_source.strategy_source_has_finish_gatekeeper_step(source) == workflows.has_finish_gatekeeper_step(source)
    assert strategy_source.normalize_strategy_source({"preset": "quality_gate"}) == workflows.normalize_workflow(
        {"preset": "quality_gate"}
    )
    assert strategy_source.build_preset_strategy_source("quality_gate") == workflows.build_preset_workflow("quality_gate")
    assert strategy_source.strategy_source_preset_names() == workflows.preset_names()
    assert strategy_source.available_strategy_prompt_templates() == workflows.available_prompt_templates()
    assert strategy_source.builtin_strategy_prompt_markdown("builder.md") == workflows.builtin_prompt_markdown("builder.md")
    assert strategy_source.resolve_strategy_prompt_files(source) == workflows.resolve_prompt_files(source)
    assert strategy_source.normalize_strategy_archetype("generator") == workflows.normalize_archetype("generator")
    assert strategy_source.strategy_archetype_display_name("builder") == workflows.display_name_for_archetype("builder")
    assert strategy_source.normalize_strategy_role_display_name("构建者", "builder") == workflows.normalize_role_display_name(
        "构建者",
        "builder",
    )
    assert strategy_source.normalize_strategy_role_models({"generator": "gpt-5.4-mini"}) == workflows.normalize_role_models(
        {"generator": "gpt-5.4-mini"}
    )
    assert strategy_source.default_strategy_role_execution_settings() == workflows.default_role_execution_settings()
    assert strategy_source.normalize_strategy_role_execution_settings({"model": "gpt-5.4"}) == workflows.normalize_role_execution_settings(
        {"model": "gpt-5.4"}
    )
    assert strategy_source.strategy_role_uses_execution_snapshot({"model": "gpt-5.4"}) == workflows.role_uses_execution_snapshot(
        {"model": "gpt-5.4"}
    )
    step_helper_cases = [
        (strategy_source.normalize_strategy_step_evidence_limit(3), workflows.normalize_step_evidence_limit(3)),
        (
            strategy_source.default_strategy_step_execution_settings(archetype="gatekeeper"),
            workflows.default_step_execution_settings(archetype="gatekeeper"),
        ),
        (
            strategy_source.normalize_strategy_step_on_pass("finish_run", archetype="gatekeeper"),
            workflows.normalize_step_on_pass("finish_run", archetype="gatekeeper"),
        ),
        (
            strategy_source.normalize_strategy_step_inherit_session(None, archetype="builder"),
            workflows.normalize_step_inherit_session(None, archetype="builder"),
        ),
        (
            strategy_source.normalize_strategy_step_action_policy({"can_block": True}, archetype="inspector"),
            workflows.normalize_step_action_policy({"can_block": True}, archetype="inspector"),
        ),
        (
            strategy_source.default_strategy_step_action_policy(archetype="builder"),
            workflows.default_step_action_policy(archetype="builder"),
        ),
        (
            strategy_source.normalize_strategy_step_parallel_group("reviewers"),
            workflows.normalize_step_parallel_group("reviewers"),
        ),
        (
            strategy_source.normalize_strategy_step_inputs({"evidence_query": {"limit": 2}}),
            workflows.normalize_step_inputs({"evidence_query": {"limit": 2}}),
        ),
    ]
    for strategy_result, workflow_result in step_helper_cases:
        assert strategy_result == workflow_result


def test_strategy_role_execution_defaults_preserve_command_only_blank_starting_point() -> None:
    settings = strategy_source.default_strategy_role_execution_settings("custom")

    assert settings == {
        "executor_kind": "custom",
        "executor_mode": "command",
        "command_cli": "",
        "command_args_text": "",
        "model": "",
        "reasoning_effort": "",
    }


def test_strategy_role_execution_settings_use_shared_alias_and_reasoning_normalization() -> None:
    settings = strategy_source.normalize_strategy_role_execution_settings(
        {
            "executor_kind": "claude-code",
            "executor_mode": " PRESET ",
            "reasoning_effort": "xhigh",
        }
    )

    assert settings == {
        "executor_kind": "claude",
        "executor_mode": "preset",
        "command_cli": "claude",
        "command_args_text": "",
        "model": "",
        "reasoning_effort": "max",
    }


def test_strategy_role_execution_settings_reject_command_only_executor_without_command_mode() -> None:
    with pytest.raises(ValueError, match="Custom Command only supports command mode"):
        strategy_source.normalize_strategy_role_execution_settings({"executor_kind": "custom"})


def test_strategy_role_execution_settings_reject_invalid_command_template() -> None:
    with pytest.raises(ValueError, match="custom command is missing required placeholders") as exc_info:
        strategy_source.normalize_strategy_role_execution_settings(
            {
                "executor_kind": "custom",
                "executor_mode": "command",
                "command_args_text": "{schema_path}",
            }
        )

    assert str(exc_info.value) == "custom command is missing required placeholders: {prompt}, {output_path}"
