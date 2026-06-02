from __future__ import annotations

from strategy_source_architecture_test_support import loopora_source


def test_strategy_source_facade_imports_strategy_source_constant_names_from_definitions() -> None:
    expected_markers = [
        (
            "strategy_source_definitions",
            "from loopora.strategy_source_errors import StrategySourceError as StrategySourceError",
        ),
        ("strategy_source_definitions", "from loopora.strategy_source_errors import WorkflowError"),
        ("strategy_source_definitions", "from loopora.strategy_source_normalization import"),
        ("strategy_source_normalization", "def normalize_strategy_source"),
        ("strategy_source_normalization", "def require_strategy_source_entries"),
        ("strategy_source_errors", "class StrategySourceError(ValueError)"),
        ("strategy_source_errors", "WorkflowError = StrategySourceError"),
        ("strategy_source_execution_settings", "def normalize_strategy_role_execution_settings"),
        ("strategy_source_execution_settings", "def strategy_role_uses_execution_snapshot"),
        ("strategy_source_validation", "def normalize_strategy_source_identifier"),
        ("strategy_source_validation", "def normalize_strategy_source_version"),
        ("strategy_source_constants", "STRATEGY_SOURCE_VERSION = 1"),
        ("strategy_source_definitions", "WORKFLOW_VERSION = STRATEGY_SOURCE_VERSION"),
        ("strategy_source_definitions", "from loopora.strategy_source_presets import"),
        ("strategy_source_presets", 'DEFAULT_STRATEGY_SOURCE_PRESET = "quality_gate"'),
        ("strategy_source_presets", "DEFAULT_WORKFLOW_PRESET = DEFAULT_STRATEGY_SOURCE_PRESET"),
        ("strategy_source_presets", "STRATEGY_SOURCE_PRESETS = build_strategy_source_presets("),
        ("strategy_source_preset_catalog", "from loopora.strategy_source_preset_compat_catalog import"),
        ("strategy_source_preset_catalog", "def build_strategy_source_presets"),
        ("strategy_source_preset_compat_catalog", "def build_strategy_source_compat_presets"),
        ("strategy_source_preset_compat_catalog", "repair_loop"),
        ("strategy_source_prompt_assets", "def parse_prompt_markdown"),
        ("strategy_source_prompt_assets", "def validate_prompt_markdown"),
        ("strategy_source_prompt_assets", "def builtin_strategy_prompt_markdown"),
        ("strategy_source_preset_catalog", "quality_gate"),
        ("strategy_source_presets", "WORKFLOW_PRESETS = STRATEGY_SOURCE_PRESETS"),
        ("strategy_source_preset_specs", "class StrategySourcePresetDefinitionSpec"),
        ("strategy_source_preset_specs", "def strategy_source_preset_definition"),
        ("strategy_source_presets", "strategy_source_preset_definition as _strategy_source_preset_definition"),
        ("strategy_source_presets", "def strategy_source_preset_copy"),
        ("strategy_source_definitions", "STRATEGY_SOURCE_ARCHETYPES = ARCHETYPES"),
        ("strategy_source_definitions", "from loopora.strategy_source_controls import"),
        ("strategy_source_definitions", "from loopora.strategy_source_files import"),
        ("strategy_source_definitions", "from loopora.strategy_source_roles import"),
        ("strategy_source_definitions", "from loopora.strategy_source_steps import"),
        ("strategy_source_definitions", "from loopora.strategy_source_validation import"),
        ("strategy_source_definitions", "from loopora.strategy_source_warnings import"),
        ("strategy_source_roles", "def normalize_strategy_archetype"),
        ("strategy_source_roles", "def normalize_strategy_source_roles"),
        ("strategy_source_roles", "def normalize_strategy_role_display_name"),
        ("strategy_source_steps", "from loopora.strategy_source_step_inputs import"),
        ("strategy_source_steps", "from loopora.strategy_source_step_policy import"),
        ("strategy_source_steps", "from loopora.strategy_source_parallel_groups import"),
        ("strategy_source_step_inputs", "def normalize_strategy_step_inputs"),
        ("strategy_source_step_inputs", "def normalize_strategy_step_evidence_query"),
        ("strategy_source_step_policy", "STEP_ACTION_POLICY_KEYS = {"),
        ("strategy_source_step_policy", "def normalize_strategy_step_action_policy"),
        ("strategy_source_parallel_groups", "PARALLEL_GROUP_ARCHETYPES = {"),
        ("strategy_source_parallel_groups", "def validate_strategy_source_parallel_groups"),
        ("strategy_source_warnings", "def strategy_source_warnings"),
        ("strategy_source_warnings", "def strategy_source_has_finish_gatekeeper_step"),
        ("strategy_source_validation", "STRATEGY_SOURCE_SAFE_IDENTIFIER_RE = re.compile"),
        ("strategy_source_validation", "WORKFLOW_SAFE_IDENTIFIER_RE = STRATEGY_SOURCE_SAFE_IDENTIFIER_RE"),
        ("strategy_source_controls", "STRATEGY_SOURCE_CONTROL_KEYS = {"),
        ("strategy_source_controls", "WORKFLOW_CONTROL_KEYS = STRATEGY_SOURCE_CONTROL_KEYS"),
        ("strategy_source_controls", "STRATEGY_SOURCE_CONTROL_AFTER_RE = re.compile"),
        ("strategy_source_controls", "WORKFLOW_CONTROL_AFTER_RE = STRATEGY_SOURCE_CONTROL_AFTER_RE"),
        ("strategy_source_files", "def resolve_strategy_prompt_files"),
        ("strategy_source_files", "def load_strategy_source_file"),
        ("strategy_source_steps", "STEP_EXECUTION_FIELDS = ("),
        ("strategy_source_steps", "def normalize_strategy_source_steps"),
        ("strategy_source_definitions", "LEGACY_STRATEGY_ROLE_BY_ARCHETYPE = LEGACY_ROLE_BY_ARCHETYPE"),
        ("strategy_source_definitions", "STRATEGY_PROMPT_FILES = PROMPT_FILES"),
        ("strategy_source_definitions", "STRATEGY_ROLE_EXECUTION_FIELDS = ROLE_EXECUTION_FIELDS"),
        ("strategy_source_definitions", "STRATEGY_ROLE_POSTURE_FIELDS = ROLE_POSTURE_FIELDS"),
    ]
    excluded_markers_by_module = {
        "strategy_source_definitions": [
            "STRATEGY_SOURCE_SAFE_IDENTIFIER_RE = re.compile",
            "STRATEGY_SOURCE_CONTROL_KEYS = {",
            "STRATEGY_SOURCE_CONTROL_AFTER_RE = re.compile",
            "STEP_EXECUTION_FIELDS = (",
            "def normalize_strategy_archetype",
            "def normalize_strategy_source_roles",
            "def strategy_source_warnings",
            "def strategy_source_has_finish_gatekeeper_step",
            "def resolve_strategy_prompt_files",
            "def load_strategy_source_file",
            "def normalize_strategy_source",
            "def require_strategy_source_entries",
            'DEFAULT_STRATEGY_SOURCE_PRESET = "quality_gate"',
            "STRATEGY_SOURCE_PRESETS = build_strategy_source_presets(",
            "def strategy_source_preset_copy",
            "class StrategySourcePresetDefinitionSpec",
        ],
        "strategy_source_steps": [
            "def normalize_strategy_step_action_policy",
            "def validate_strategy_source_parallel_groups",
        ],
        "strategy_source_presets": [
            "class StrategySourcePresetDefinitionSpec",
            "def strategy_source_preset_definition",
        ],
        "strategy_source": [
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
        ],
    }
    sources = _strategy_source_sources(expected_markers, excluded_markers_by_module)

    for module_name, marker in expected_markers:
        assert marker in sources[module_name]
    for module_name, markers in excluded_markers_by_module.items():
        for marker in markers:
            assert marker not in sources[module_name]


def _strategy_source_sources(expected_markers: list[tuple[str, str]], excluded_markers_by_module: dict[str, list[str]]) -> dict:
    module_names = {module_name for module_name, _marker in expected_markers} | set(excluded_markers_by_module)
    return {module_name: loopora_source(f"{module_name}.py") for module_name in module_names}
