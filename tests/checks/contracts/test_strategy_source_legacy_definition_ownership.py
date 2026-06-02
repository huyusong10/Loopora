from __future__ import annotations

from strategy_source_architecture_test_support import loopora_source


def test_strategy_source_definitions_own_legacy_workflow_format_implementation() -> None:
    strategy_source_source = loopora_source("strategy_source.py")
    strategy_definitions_source = loopora_source("strategy_source_definitions.py")
    strategy_controls_source = loopora_source("strategy_source_controls.py")
    strategy_preset_catalog_source = loopora_source("strategy_source_preset_catalog.py")
    strategy_presets_source = loopora_source("strategy_source_presets.py")
    strategy_prompt_assets_source = loopora_source("strategy_source_prompt_assets.py")
    strategy_roles_source = loopora_source("strategy_source_roles.py")
    strategy_steps_source = loopora_source("strategy_source_steps.py")
    strategy_warnings_source = loopora_source("strategy_source_warnings.py")
    strategy_execution_source = loopora_source("strategy_source_execution_settings.py")
    strategy_validation_source = loopora_source("strategy_source_validation.py")
    strategy_errors_source = loopora_source("strategy_source_errors.py")
    strategy_files_source = loopora_source("strategy_source_files.py")
    strategy_normalization_source = loopora_source("strategy_source_normalization.py")
    workflow_compat_source = loopora_source("workflows.py")
    expected_markers = [
        (strategy_source_source, "from loopora.strategy_source_definitions import"),
        (strategy_definitions_source, "from loopora.strategy_source_controls import"),
        (strategy_definitions_source, "from loopora.strategy_source_files import"),
        (strategy_definitions_source, "from loopora.strategy_source_prompt_assets import"),
        (strategy_definitions_source, "from loopora.strategy_source_execution_settings import"),
        (strategy_definitions_source, "from loopora.strategy_source_roles import"),
        (strategy_definitions_source, "from loopora.strategy_source_steps import"),
        (strategy_definitions_source, "from loopora.strategy_source_validation import"),
        (strategy_definitions_source, "from loopora.strategy_source_warnings import"),
        (strategy_definitions_source, "from loopora.strategy_source_presets import"),
        (strategy_definitions_source, "from loopora.strategy_source_normalization import"),
        (strategy_normalization_source, "def normalize_strategy_source"),
        (strategy_errors_source, "class StrategySourceError(ValueError)"),
        (loopora_source("strategy_source_preset_specs.py"), "class StrategySourcePresetDefinitionSpec"),
        (strategy_presets_source, "from loopora.strategy_source_preset_specs import"),
        (strategy_presets_source, "def strategy_source_preset_copy"),
        (strategy_presets_source, "STRATEGY_SOURCE_PRESETS = build_strategy_source_presets("),
        (strategy_preset_catalog_source, "def build_strategy_source_presets"),
        (strategy_prompt_assets_source, "def parse_prompt_markdown"),
        (strategy_prompt_assets_source, "def builtin_strategy_prompt_markdown"),
        (strategy_execution_source, "def normalize_strategy_role_execution_settings"),
        (strategy_validation_source, "def normalize_strategy_source_identifier"),
        (strategy_validation_source, "def normalize_strategy_source_version"),
        (strategy_validation_source, "def normalize_string_list"),
        (strategy_validation_source, "def unknown_keys"),
        (strategy_controls_source, "def normalize_strategy_source_controls"),
        (strategy_controls_source, "STRATEGY_SOURCE_CONTROL_KEYS = {"),
        (strategy_files_source, "def resolve_strategy_prompt_files"),
        (strategy_files_source, "def load_strategy_source_file"),
        (strategy_roles_source, "def normalize_strategy_archetype"),
        (strategy_roles_source, "def normalize_strategy_role_display_name"),
        (strategy_roles_source, "def normalize_strategy_source_roles"),
        (strategy_steps_source, "from loopora.strategy_source_parallel_groups import"),
        (strategy_steps_source, "def default_strategy_step_execution_settings"),
        (strategy_steps_source, "def normalize_strategy_source_steps"),
        (strategy_warnings_source, "def strategy_source_warnings"),
        (strategy_warnings_source, "def strategy_source_has_finish_gatekeeper_step"),
        (strategy_preset_catalog_source, "build_then_parallel_review"),
        (strategy_presets_source, "workflow_preset_copy = strategy_source_preset_copy"),
        (strategy_source_source, "definition_strategy_source_preset_copy"),
        (strategy_definitions_source, "Strategy Source definitions"),
        (workflow_compat_source, "Legacy workflow import compatibility"),
        (workflow_compat_source, "from loopora import strategy_source_definitions as _definitions"),
        (workflow_compat_source, "globals().update({name: getattr(_definitions, name) for name in __all__})"),
    ]
    for source, marker in expected_markers:
        assert marker in source
    excluded_markers = [
        (strategy_source_source, "from loopora.workflows import"),
        (strategy_definitions_source, "class WorkflowPresetDefinitionSpec"),
        (strategy_definitions_source, "def _workflow_preset_definition"),
        (strategy_definitions_source, "def parse_prompt_markdown"),
        (strategy_definitions_source, "def builtin_strategy_prompt_markdown"),
        (strategy_definitions_source, "def normalize_strategy_role_execution_settings"),
        (strategy_definitions_source, "def normalize_strategy_source_identifier"),
        (strategy_definitions_source, "def normalize_strategy_source_version"),
        (strategy_definitions_source, "def normalize_strategy_source_controls"),
        (strategy_definitions_source, "def resolve_strategy_prompt_files"),
        (strategy_definitions_source, "def load_strategy_source_file"),
        (strategy_definitions_source, "def normalize_strategy_source"),
        (strategy_definitions_source, "def normalize_strategy_archetype"),
        (strategy_definitions_source, "def normalize_strategy_role_display_name"),
        (strategy_definitions_source, "def normalize_strategy_source_roles"),
        (strategy_definitions_source, "def strategy_source_warnings"),
        (strategy_definitions_source, "def strategy_source_has_finish_gatekeeper_step"),
        (strategy_definitions_source, "STRATEGY_SOURCE_CONTROL_KEYS = {"),
        (strategy_definitions_source, "def default_strategy_step_execution_settings"),
        (strategy_definitions_source, "def normalize_strategy_source_steps"),
        (strategy_definitions_source, "def validate_strategy_source_parallel_groups"),
        (strategy_definitions_source, "class StrategySourcePresetDefinitionSpec"),
        (strategy_definitions_source, "def _strategy_source_preset_definition"),
        (strategy_definitions_source, "def strategy_source_preset_copy"),
        (strategy_definitions_source, "STRATEGY_SOURCE_PRESETS = build_strategy_source_presets("),
        (strategy_definitions_source, "workflow_preset_copy = strategy_source_preset_copy"),
        (strategy_source_source, "workflow_preset_copy"),
        (workflow_compat_source, "from loopora.strategy_source_definitions import *"),
        (workflow_compat_source, "def normalize_workflow"),
    ]
    for source, marker in excluded_markers:
        assert marker not in source
