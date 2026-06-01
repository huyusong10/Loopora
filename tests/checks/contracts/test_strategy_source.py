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
    strategy_normalization_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_normalization.py").read_text(
        encoding="utf-8"
    )
    strategy_presets_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_presets.py").read_text(
        encoding="utf-8"
    )
    strategy_controls_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_controls.py").read_text(
        encoding="utf-8"
    )
    strategy_files_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_files.py").read_text(encoding="utf-8")
    strategy_prompt_assets_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_prompt_assets.py").read_text(
        encoding="utf-8"
    )
    strategy_roles_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_roles.py").read_text(encoding="utf-8")
    strategy_step_inputs_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_step_inputs.py").read_text(
        encoding="utf-8"
    )
    strategy_step_policy_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_step_policy.py").read_text(
        encoding="utf-8"
    )
    strategy_parallel_groups_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_parallel_groups.py").read_text(
        encoding="utf-8"
    )
    strategy_steps_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_steps.py").read_text(encoding="utf-8")
    strategy_warnings_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_warnings.py").read_text(
        encoding="utf-8"
    )
    strategy_execution_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_execution_settings.py").read_text(
        encoding="utf-8"
    )
    strategy_validation_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_validation.py").read_text(
        encoding="utf-8"
    )
    normalization_names = [
        "normalize_strategy_source",
    ]
    preset_names = [
        "build_preset_strategy_source",
        "strategy_source_preset_names",
        "strategy_source_preset_copy",
    ]
    file_names = [
        "resolve_strategy_prompt_files",
        "load_strategy_source_file",
    ]
    warning_names = [
        "strategy_source_has_finish_gatekeeper_step",
        "strategy_source_warnings",
    ]
    role_names = [
        "normalize_strategy_archetype",
        "strategy_archetype_display_name",
        "normalize_strategy_role_display_name",
        "normalize_strategy_role_models",
    ]
    step_input_names = [
        "normalize_strategy_step_evidence_limit",
        "normalize_strategy_step_inputs",
    ]
    step_names = [
        "default_strategy_step_execution_settings",
        "normalize_strategy_step_on_pass",
        "normalize_strategy_step_inherit_session",
    ]
    step_policy_names = [
        "normalize_strategy_step_action_policy",
        "default_strategy_step_action_policy",
    ]
    parallel_group_names = [
        "normalize_strategy_step_parallel_group",
        "validate_strategy_source_parallel_groups",
    ]
    control_names = [
        "normalize_strategy_source_controls",
    ]
    execution_names = [
        "default_strategy_role_execution_settings",
        "normalize_strategy_role_execution_settings",
        "strategy_role_uses_execution_snapshot",
    ]
    validation_names = [
        "normalize_strategy_source_identifier",
        "normalize_strategy_source_version",
    ]
    prompt_asset_names = [
        "available_strategy_prompt_templates",
        "builtin_strategy_prompt_markdown",
        "load_strategy_prompt_file",
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
            "normalize_workflow_version",
        "normalize_workflow_controls",
        "return has_finish_gatekeeper_step(",
        "workflow_warnings",
        "validate_workflow_parallel_groups",
        "load_workflow_file",
    ]

    for name in normalization_names:
        assert f"def {name}" in strategy_normalization_source
        assert f"def {name}" not in strategy_definitions_source
        assert f"definition_{name}" in strategy_source_source
    for name in preset_names:
        assert f"def {name}" in strategy_presets_source
        assert f"def {name}" not in strategy_definitions_source
        assert f"definition_{name}" in strategy_source_source
    ownership_groups = [
        (strategy_controls_source, control_names),
            (strategy_files_source, file_names),
            (strategy_roles_source, role_names),
            (strategy_step_inputs_source, step_input_names),
            (strategy_step_policy_source, step_policy_names),
            (strategy_parallel_groups_source, parallel_group_names),
            (strategy_steps_source, step_names),
        (strategy_warnings_source, warning_names),
        (strategy_execution_source, execution_names),
        (strategy_validation_source, validation_names),
        (strategy_prompt_assets_source, prompt_asset_names),
    ]
    for owner_source, names in ownership_groups:
        for name in names:
            assert f"def {name}" in owner_source
            assert f"def {name}" not in strategy_definitions_source
            assert f"definition_{name}" in strategy_source_source
    for marker in old_facade_markers:
        assert marker not in strategy_source_source


def test_strategy_source_facade_imports_strategy_source_constant_names_from_definitions() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    strategy_definitions_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_definitions.py").read_text(
        encoding="utf-8"
    )
    strategy_presets_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_presets.py").read_text(
        encoding="utf-8"
    )
    strategy_controls_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_controls.py").read_text(
        encoding="utf-8"
    )
    strategy_constants_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_constants.py").read_text(
        encoding="utf-8"
    )
    strategy_errors_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_errors.py").read_text(
        encoding="utf-8"
    )
    strategy_files_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_files.py").read_text(encoding="utf-8")
    strategy_prompt_assets_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_prompt_assets.py").read_text(
        encoding="utf-8"
    )
    strategy_roles_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_roles.py").read_text(encoding="utf-8")
    strategy_step_inputs_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_step_inputs.py").read_text(
        encoding="utf-8"
    )
    strategy_step_policy_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_step_policy.py").read_text(
        encoding="utf-8"
    )
    strategy_parallel_groups_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_parallel_groups.py").read_text(
        encoding="utf-8"
    )
    strategy_steps_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_steps.py").read_text(encoding="utf-8")
    strategy_warnings_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_warnings.py").read_text(
        encoding="utf-8"
    )
    strategy_execution_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_execution_settings.py").read_text(
        encoding="utf-8"
    )
    strategy_validation_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_validation.py").read_text(
        encoding="utf-8"
    )
    strategy_preset_catalog_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_preset_catalog.py").read_text(
        encoding="utf-8"
    )
    strategy_preset_specs_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_preset_specs.py").read_text(
        encoding="utf-8"
    )
    strategy_preset_compat_source = (
        REPO_ROOT / "src" / "loopora" / "strategy_source_preset_compat_catalog.py"
    ).read_text(encoding="utf-8")
    strategy_normalization_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_normalization.py").read_text(
        encoding="utf-8"
    )

    expected_markers = [
        (strategy_definitions_source, "from loopora.strategy_source_errors import StrategySourceError as StrategySourceError"),
        (strategy_definitions_source, "from loopora.strategy_source_errors import WorkflowError"),
        (strategy_definitions_source, "from loopora.strategy_source_normalization import"),
        (strategy_normalization_source, "def normalize_strategy_source"),
        (strategy_normalization_source, "def require_strategy_source_entries"),
        (strategy_errors_source, "class StrategySourceError(ValueError)"),
        (strategy_errors_source, "WorkflowError = StrategySourceError"),
        (strategy_execution_source, "def normalize_strategy_role_execution_settings"),
        (strategy_execution_source, "def strategy_role_uses_execution_snapshot"),
        (strategy_validation_source, "def normalize_strategy_source_identifier"),
        (strategy_validation_source, "def normalize_strategy_source_version"),
        (strategy_constants_source, "STRATEGY_SOURCE_VERSION = 1"),
        (strategy_definitions_source, "WORKFLOW_VERSION = STRATEGY_SOURCE_VERSION"),
        (strategy_definitions_source, "from loopora.strategy_source_presets import"),
        (strategy_presets_source, 'DEFAULT_STRATEGY_SOURCE_PRESET = "quality_gate"'),
        (strategy_presets_source, "DEFAULT_WORKFLOW_PRESET = DEFAULT_STRATEGY_SOURCE_PRESET"),
        (strategy_presets_source, "STRATEGY_SOURCE_PRESETS = build_strategy_source_presets("),
        (strategy_preset_catalog_source, "from loopora.strategy_source_preset_compat_catalog import"),
        (strategy_preset_catalog_source, "def build_strategy_source_presets"),
        (strategy_preset_compat_source, "def build_strategy_source_compat_presets"),
        (strategy_preset_compat_source, "repair_loop"),
        (strategy_prompt_assets_source, "def parse_prompt_markdown"),
        (strategy_prompt_assets_source, "def validate_prompt_markdown"),
        (strategy_prompt_assets_source, "def builtin_strategy_prompt_markdown"),
        (strategy_preset_catalog_source, "quality_gate"),
        (strategy_presets_source, "WORKFLOW_PRESETS = STRATEGY_SOURCE_PRESETS"),
        (strategy_preset_specs_source, "class StrategySourcePresetDefinitionSpec"),
        (strategy_preset_specs_source, "def strategy_source_preset_definition"),
        (strategy_presets_source, "strategy_source_preset_definition as _strategy_source_preset_definition"),
        (strategy_presets_source, "def strategy_source_preset_copy"),
        (strategy_definitions_source, "STRATEGY_SOURCE_ARCHETYPES = ARCHETYPES"),
        (strategy_definitions_source, "from loopora.strategy_source_controls import"),
        (strategy_definitions_source, "from loopora.strategy_source_files import"),
        (strategy_definitions_source, "from loopora.strategy_source_roles import"),
        (strategy_definitions_source, "from loopora.strategy_source_steps import"),
        (strategy_definitions_source, "from loopora.strategy_source_validation import"),
        (strategy_definitions_source, "from loopora.strategy_source_warnings import"),
        (strategy_roles_source, "def normalize_strategy_archetype"),
        (strategy_roles_source, "def normalize_strategy_source_roles"),
        (strategy_roles_source, "def normalize_strategy_role_display_name"),
        (strategy_steps_source, "from loopora.strategy_source_step_inputs import"),
        (strategy_steps_source, "from loopora.strategy_source_step_policy import"),
        (strategy_steps_source, "from loopora.strategy_source_parallel_groups import"),
        (strategy_step_inputs_source, "def normalize_strategy_step_inputs"),
        (strategy_step_inputs_source, "def normalize_strategy_step_evidence_query"),
        (strategy_step_policy_source, "STEP_ACTION_POLICY_KEYS = {"),
        (strategy_step_policy_source, "def normalize_strategy_step_action_policy"),
        (strategy_parallel_groups_source, "PARALLEL_GROUP_ARCHETYPES = {"),
        (strategy_parallel_groups_source, "def validate_strategy_source_parallel_groups"),
        (strategy_warnings_source, "def strategy_source_warnings"),
        (strategy_warnings_source, "def strategy_source_has_finish_gatekeeper_step"),
        (strategy_validation_source, "STRATEGY_SOURCE_SAFE_IDENTIFIER_RE = re.compile"),
        (strategy_validation_source, "WORKFLOW_SAFE_IDENTIFIER_RE = STRATEGY_SOURCE_SAFE_IDENTIFIER_RE"),
        (strategy_controls_source, "STRATEGY_SOURCE_CONTROL_KEYS = {"),
        (strategy_controls_source, "WORKFLOW_CONTROL_KEYS = STRATEGY_SOURCE_CONTROL_KEYS"),
        (strategy_controls_source, "STRATEGY_SOURCE_CONTROL_AFTER_RE = re.compile"),
        (strategy_controls_source, "WORKFLOW_CONTROL_AFTER_RE = STRATEGY_SOURCE_CONTROL_AFTER_RE"),
        (strategy_files_source, "def resolve_strategy_prompt_files"),
        (strategy_files_source, "def load_strategy_source_file"),
        (strategy_steps_source, "STEP_EXECUTION_FIELDS = ("),
        (strategy_steps_source, "def normalize_strategy_source_steps"),
        (strategy_definitions_source, "LEGACY_STRATEGY_ROLE_BY_ARCHETYPE = LEGACY_ROLE_BY_ARCHETYPE"),
        (strategy_definitions_source, "STRATEGY_PROMPT_FILES = PROMPT_FILES"),
        (strategy_definitions_source, "STRATEGY_ROLE_EXECUTION_FIELDS = ROLE_EXECUTION_FIELDS"),
        (strategy_definitions_source, "STRATEGY_ROLE_POSTURE_FIELDS = ROLE_POSTURE_FIELDS"),
    ]
    for source, marker in expected_markers:
        assert marker in source
    assert "STRATEGY_SOURCE_SAFE_IDENTIFIER_RE = re.compile" not in strategy_definitions_source
    assert "STRATEGY_SOURCE_CONTROL_KEYS = {" not in strategy_definitions_source
    assert "STRATEGY_SOURCE_CONTROL_AFTER_RE = re.compile" not in strategy_definitions_source
    assert "STEP_EXECUTION_FIELDS = (" not in strategy_definitions_source
    assert "def normalize_strategy_archetype" not in strategy_definitions_source
    assert "def normalize_strategy_source_roles" not in strategy_definitions_source
    assert "def strategy_source_warnings" not in strategy_definitions_source
    assert "def strategy_source_has_finish_gatekeeper_step" not in strategy_definitions_source
    assert "def normalize_strategy_step_action_policy" not in strategy_steps_source
    assert "def validate_strategy_source_parallel_groups" not in strategy_steps_source
    assert "def resolve_strategy_prompt_files" not in strategy_definitions_source
    assert "def load_strategy_source_file" not in strategy_definitions_source
    assert "def normalize_strategy_source" not in strategy_definitions_source
    assert "def require_strategy_source_entries" not in strategy_definitions_source
    assert 'DEFAULT_STRATEGY_SOURCE_PRESET = "quality_gate"' not in strategy_definitions_source
    assert "STRATEGY_SOURCE_PRESETS = build_strategy_source_presets(" not in strategy_definitions_source
    assert "def strategy_source_preset_copy" not in strategy_definitions_source
    assert "class StrategySourcePresetDefinitionSpec" not in strategy_definitions_source
    assert "class StrategySourcePresetDefinitionSpec" not in strategy_presets_source
    assert "def strategy_source_preset_definition" not in strategy_presets_source

    facade_excluded_markers = [
        "class StrategySourceError(ValueError)",
        "WorkflowError = StrategySourceError",
        'DEFAULT_STRATEGY_SOURCE_PRESET = "quality_gate"',
        "DEFAULT_WORKFLOW_PRESET = DEFAULT_STRATEGY_SOURCE_PRESET",
        "STRATEGY_SOURCE_PRESETS = {",
        "WORKFLOW_PRESETS = STRATEGY_SOURCE_PRESETS",
        "STRATEGY_SOURCE_ARCHETYPES = ARCHETYPES",
        "LEGACY_STRATEGY_ROLE_BY_ARCHETYPE = LEGACY_ROLE_BY_ARCHETYPE",
        "STRATEGY_PROMPT_FILES = PROMPT_FILES",
        "STRATEGY_ROLE_EXECUTION_FIELDS = ROLE_EXECUTION_FIELDS",
        "STRATEGY_ROLE_POSTURE_FIELDS = ROLE_POSTURE_FIELDS",
    ]
    for marker in facade_excluded_markers:
        assert marker not in strategy_source_source
