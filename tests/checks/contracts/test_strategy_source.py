from __future__ import annotations

from pathlib import Path

from loopora.strategy_source import (
    DEFAULT_STRATEGY_SOURCE_PRESET,
    LEGACY_STRATEGY_ROLE_BY_ARCHETYPE,
    STRATEGY_PROMPT_FILES,
    STRATEGY_ROLE_EXECUTION_FIELDS,
    STRATEGY_ROLE_POSTURE_FIELDS,
    STRATEGY_SOURCE_ARCHETYPES,
    StrategySourceError,
    available_strategy_prompt_templates,
    build_preset_strategy_source,
    builtin_strategy_prompt_markdown,
    default_strategy_role_execution_settings,
    default_strategy_step_action_policy,
    default_strategy_step_execution_settings,
    normalize_strategy_source,
    normalize_strategy_source_identifier,
    normalize_strategy_source_version,
    normalize_strategy_archetype,
    normalize_strategy_role_display_name,
    normalize_strategy_role_execution_settings,
    normalize_strategy_role_models,
    normalize_strategy_step_action_policy,
    normalize_strategy_step_evidence_limit,
    normalize_strategy_step_inherit_session,
    normalize_strategy_step_inputs,
    normalize_strategy_step_on_pass,
    normalize_strategy_step_parallel_group,
    resolve_strategy_prompt_files,
    strategy_archetype_display_name,
    strategy_role_uses_execution_snapshot,
    strategy_source_has_finish_gatekeeper_step,
    strategy_source_preset_copy,
    strategy_source_preset_names,
    strategy_source_warnings,
)
from loopora.workflows import (
    DEFAULT_WORKFLOW_PRESET,
    ARCHETYPES,
    LEGACY_ROLE_BY_ARCHETYPE,
    PROMPT_FILES,
    ROLE_EXECUTION_FIELDS,
    ROLE_POSTURE_FIELDS,
    WorkflowError,
    available_prompt_templates,
    build_preset_workflow,
    builtin_prompt_markdown,
    default_role_execution_settings,
    default_step_action_policy,
    default_step_execution_settings,
    display_name_for_archetype,
    has_finish_gatekeeper_step,
    normalize_workflow,
    normalize_workflow_identifier,
    normalize_workflow_version,
    normalize_archetype,
    normalize_role_display_name,
    normalize_role_execution_settings,
    normalize_role_models,
    normalize_step_action_policy,
    normalize_step_evidence_limit,
    normalize_step_inherit_session,
    normalize_step_inputs,
    normalize_step_on_pass,
    normalize_step_parallel_group,
    preset_names,
    resolve_prompt_files,
    role_uses_execution_snapshot,
    workflow_preset_copy,
    workflow_warnings,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_strategy_source_preset_copy_preserves_legacy_workflow_copy_contract() -> None:
    assert strategy_source_preset_copy("quality_gate") == workflow_preset_copy("quality_gate")


def test_strategy_source_constants_preserve_legacy_workflow_constant_contract() -> None:
    assert StrategySourceError is WorkflowError
    assert DEFAULT_STRATEGY_SOURCE_PRESET == DEFAULT_WORKFLOW_PRESET
    assert STRATEGY_SOURCE_ARCHETYPES == ARCHETYPES
    assert LEGACY_STRATEGY_ROLE_BY_ARCHETYPE == LEGACY_ROLE_BY_ARCHETYPE
    assert STRATEGY_PROMPT_FILES == PROMPT_FILES
    assert STRATEGY_ROLE_EXECUTION_FIELDS == ROLE_EXECUTION_FIELDS
    assert STRATEGY_ROLE_POSTURE_FIELDS == ROLE_POSTURE_FIELDS


def test_strategy_source_helpers_preserve_legacy_workflow_helper_contract() -> None:
    strategy_source = {
        "version": 1,
        "roles": [
            {"id": "builder", "archetype": "builder", "prompt_ref": "builder.md"},
        ],
        "steps": [
            {"id": "builder_step", "role_id": "builder"},
        ],
    }

    assert normalize_strategy_source_identifier("builder_step", field_name="step id") == normalize_workflow_identifier(
        "builder_step",
        field_name="step id",
    )
    assert normalize_strategy_source_version(None) == normalize_workflow_version(None)
    assert strategy_source_warnings(strategy_source) == workflow_warnings(strategy_source)
    assert strategy_source_has_finish_gatekeeper_step(strategy_source) == has_finish_gatekeeper_step(strategy_source)
    assert normalize_strategy_source({"preset": "quality_gate"}) == normalize_workflow({"preset": "quality_gate"})
    assert build_preset_strategy_source("quality_gate") == build_preset_workflow("quality_gate")
    assert strategy_source_preset_names() == preset_names()
    assert available_strategy_prompt_templates() == available_prompt_templates()
    assert builtin_strategy_prompt_markdown("builder.md") == builtin_prompt_markdown("builder.md")
    assert resolve_strategy_prompt_files(strategy_source) == resolve_prompt_files(strategy_source)
    assert normalize_strategy_archetype("generator") == normalize_archetype("generator")
    assert strategy_archetype_display_name("builder") == display_name_for_archetype("builder")
    assert normalize_strategy_role_display_name("构建者", "builder") == normalize_role_display_name("构建者", "builder")
    assert normalize_strategy_role_models({"generator": "gpt-5.4-mini"}) == normalize_role_models(
        {"generator": "gpt-5.4-mini"}
    )
    assert default_strategy_role_execution_settings() == default_role_execution_settings()
    assert normalize_strategy_role_execution_settings({"model": "gpt-5.4"}) == normalize_role_execution_settings(
        {"model": "gpt-5.4"}
    )
    assert strategy_role_uses_execution_snapshot({"model": "gpt-5.4"}) == role_uses_execution_snapshot(
        {"model": "gpt-5.4"}
    )
    strategy_step_helper_cases = [
        (normalize_strategy_step_evidence_limit(3), normalize_step_evidence_limit(3)),
        (
            default_strategy_step_execution_settings(archetype="gatekeeper"),
            default_step_execution_settings(archetype="gatekeeper"),
        ),
        (
            normalize_strategy_step_on_pass("finish_run", archetype="gatekeeper"),
            normalize_step_on_pass("finish_run", archetype="gatekeeper"),
        ),
        (
            normalize_strategy_step_inherit_session(None, archetype="builder"),
            normalize_step_inherit_session(None, archetype="builder"),
        ),
        (
            normalize_strategy_step_action_policy({"can_block": True}, archetype="inspector"),
            normalize_step_action_policy({"can_block": True}, archetype="inspector"),
        ),
        (default_strategy_step_action_policy(archetype="builder"), default_step_action_policy(archetype="builder")),
        (normalize_strategy_step_parallel_group("reviewers"), normalize_step_parallel_group("reviewers")),
        (
            normalize_strategy_step_inputs({"evidence_query": {"limit": 2}}),
            normalize_step_inputs({"evidence_query": {"limit": 2}}),
        ),
    ]
    for strategy_result, workflow_result in strategy_step_helper_cases:
        assert strategy_result == workflow_result


def test_strategy_source_facade_uses_strategy_source_helper_names_for_legacy_workflow_helpers() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    strategy_definitions_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_definitions.py").read_text(
        encoding="utf-8"
    )
    definition_names = [
        "normalize_strategy_source_identifier",
        "normalize_strategy_source",
        "build_preset_strategy_source",
        "strategy_source_preset_names",
        "available_strategy_prompt_templates",
        "builtin_strategy_prompt_markdown",
        "load_strategy_prompt_file",
        "resolve_strategy_prompt_files",
        "normalize_strategy_archetype",
        "strategy_archetype_display_name",
        "normalize_strategy_role_display_name",
        "normalize_strategy_role_models",
        "default_strategy_role_execution_settings",
        "normalize_strategy_role_execution_settings",
        "strategy_role_uses_execution_snapshot",
        "normalize_strategy_step_evidence_limit",
        "default_strategy_step_execution_settings",
        "normalize_strategy_step_on_pass",
        "normalize_strategy_step_inherit_session",
        "normalize_strategy_step_action_policy",
        "default_strategy_step_action_policy",
        "normalize_strategy_step_parallel_group",
        "normalize_strategy_step_inputs",
        "normalize_strategy_source_version",
        "normalize_strategy_source_controls",
        "strategy_source_has_finish_gatekeeper_step",
        "strategy_source_warnings",
        "validate_strategy_source_parallel_groups",
        "load_strategy_source_file",
    ]
    old_facade_markers = [
        "normalize_workflow_identifier",
        "normalize_workflow",
        "build_preset_workflow",
        "    preset_names,",
        "return preset_names(",
        "available_prompt_templates",
        "builtin_prompt_markdown",
        "load_prompt_file",
        "resolve_prompt_files",
        "return normalize_archetype(",
        "return display_name_for_archetype(",
        "return normalize_role_display_name(",
        "return normalize_role_models(",
        "return default_role_execution_settings(",
        "return normalize_role_execution_settings(",
        "return role_uses_execution_snapshot(",
        "return normalize_step_evidence_limit(",
        "return default_step_execution_settings(",
        "return normalize_step_on_pass(",
        "return normalize_step_inherit_session(",
        "return normalize_step_action_policy(",
        "return default_step_action_policy(",
        "return normalize_step_parallel_group(",
        "return normalize_step_inputs(",
        "normalize_workflow_version",
        "normalize_workflow_controls",
        "return has_finish_gatekeeper_step(",
        "workflow_warnings",
        "validate_workflow_parallel_groups",
        "load_workflow_file",
    ]

    for name in definition_names:
        assert f"def {name}" in strategy_definitions_source
        assert f"definition_{name}" in strategy_source_source
    for marker in old_facade_markers:
        assert marker not in strategy_source_source


def test_strategy_source_facade_imports_strategy_source_constant_names_from_definitions() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    strategy_definitions_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_definitions.py").read_text(
        encoding="utf-8"
    )

    assert "class StrategySourceError(ValueError)" in strategy_definitions_source
    assert "WorkflowError = StrategySourceError" in strategy_definitions_source
    assert "STRATEGY_SOURCE_VERSION = 1" in strategy_definitions_source
    assert "WORKFLOW_VERSION = STRATEGY_SOURCE_VERSION" in strategy_definitions_source
    assert 'DEFAULT_STRATEGY_SOURCE_PRESET = "quality_gate"' in strategy_definitions_source
    assert "DEFAULT_WORKFLOW_PRESET = DEFAULT_STRATEGY_SOURCE_PRESET" in strategy_definitions_source
    assert "STRATEGY_SOURCE_PRESETS = {" in strategy_definitions_source
    assert "WORKFLOW_PRESETS = STRATEGY_SOURCE_PRESETS" in strategy_definitions_source
    assert "STRATEGY_SOURCE_ARCHETYPES = ARCHETYPES" in strategy_definitions_source
    assert "STRATEGY_SOURCE_SAFE_IDENTIFIER_RE = re.compile" in strategy_definitions_source
    assert "WORKFLOW_SAFE_IDENTIFIER_RE = STRATEGY_SOURCE_SAFE_IDENTIFIER_RE" in strategy_definitions_source
    assert "STRATEGY_SOURCE_CONTROL_KEYS = {" in strategy_definitions_source
    assert "WORKFLOW_CONTROL_KEYS = STRATEGY_SOURCE_CONTROL_KEYS" in strategy_definitions_source
    assert "STRATEGY_SOURCE_CONTROL_AFTER_RE = re.compile" in strategy_definitions_source
    assert "WORKFLOW_CONTROL_AFTER_RE = STRATEGY_SOURCE_CONTROL_AFTER_RE" in strategy_definitions_source
    assert "LEGACY_STRATEGY_ROLE_BY_ARCHETYPE = LEGACY_ROLE_BY_ARCHETYPE" in strategy_definitions_source
    assert "STRATEGY_PROMPT_FILES = PROMPT_FILES" in strategy_definitions_source
    assert "STRATEGY_ROLE_EXECUTION_FIELDS = ROLE_EXECUTION_FIELDS" in strategy_definitions_source
    assert "STRATEGY_ROLE_POSTURE_FIELDS = ROLE_POSTURE_FIELDS" in strategy_definitions_source
    assert "class StrategySourceError(ValueError)" not in strategy_source_source
    assert "WorkflowError = StrategySourceError" not in strategy_source_source
    assert 'DEFAULT_STRATEGY_SOURCE_PRESET = "quality_gate"' not in strategy_source_source
    assert "DEFAULT_WORKFLOW_PRESET = DEFAULT_STRATEGY_SOURCE_PRESET" not in strategy_source_source
    assert "STRATEGY_SOURCE_PRESETS = {" not in strategy_source_source
    assert "WORKFLOW_PRESETS = STRATEGY_SOURCE_PRESETS" not in strategy_source_source
    assert "STRATEGY_SOURCE_ARCHETYPES = ARCHETYPES" not in strategy_source_source
    assert "LEGACY_STRATEGY_ROLE_BY_ARCHETYPE = LEGACY_ROLE_BY_ARCHETYPE" not in strategy_source_source
    assert "STRATEGY_PROMPT_FILES = PROMPT_FILES" not in strategy_source_source
    assert "STRATEGY_ROLE_EXECUTION_FIELDS = ROLE_EXECUTION_FIELDS" not in strategy_source_source
    assert "STRATEGY_ROLE_POSTURE_FIELDS = ROLE_POSTURE_FIELDS" not in strategy_source_source
