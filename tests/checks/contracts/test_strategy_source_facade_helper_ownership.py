from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _loopora_source(module_name: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / f"{module_name}.py").read_text(encoding="utf-8")


def test_strategy_source_facade_uses_strategy_source_helper_names_for_legacy_workflow_helpers() -> None:
    facade_source = _loopora_source("strategy_source")
    definitions_source = _loopora_source("strategy_source_definitions")
    owner_sources = {
        "strategy_source_controls": _loopora_source("strategy_source_controls"),
        "strategy_source_execution_settings": _loopora_source("strategy_source_execution_settings"),
        "strategy_source_files": _loopora_source("strategy_source_files"),
        "strategy_source_normalization": _loopora_source("strategy_source_normalization"),
        "strategy_source_parallel_groups": _loopora_source("strategy_source_parallel_groups"),
        "strategy_source_presets": _loopora_source("strategy_source_presets"),
        "strategy_source_prompt_assets": _loopora_source("strategy_source_prompt_assets"),
        "strategy_source_roles": _loopora_source("strategy_source_roles"),
        "strategy_source_step_inputs": _loopora_source("strategy_source_step_inputs"),
        "strategy_source_step_policy": _loopora_source("strategy_source_step_policy"),
        "strategy_source_steps": _loopora_source("strategy_source_steps"),
        "strategy_source_validation": _loopora_source("strategy_source_validation"),
        "strategy_source_warnings": _loopora_source("strategy_source_warnings"),
    }
    ownership_groups = [
        ("strategy_source_normalization", ["normalize_strategy_source"]),
        (
            "strategy_source_presets",
            ["build_preset_strategy_source", "strategy_source_preset_names", "strategy_source_preset_copy"],
        ),
        ("strategy_source_controls", ["normalize_strategy_source_controls"]),
        ("strategy_source_files", ["resolve_strategy_prompt_files", "load_strategy_source_file"]),
        (
            "strategy_source_roles",
            [
                "normalize_strategy_archetype",
                "strategy_archetype_display_name",
                "normalize_strategy_role_display_name",
                "normalize_strategy_role_models",
            ],
        ),
        (
            "strategy_source_step_inputs",
            ["normalize_strategy_step_evidence_limit", "normalize_strategy_step_inputs"],
        ),
        (
            "strategy_source_step_policy",
            ["normalize_strategy_step_action_policy", "default_strategy_step_action_policy"],
        ),
        (
            "strategy_source_parallel_groups",
            ["normalize_strategy_step_parallel_group", "validate_strategy_source_parallel_groups"],
        ),
        (
            "strategy_source_steps",
            [
                "default_strategy_step_execution_settings",
                "normalize_strategy_step_on_pass",
                "normalize_strategy_step_inherit_session",
            ],
        ),
        (
            "strategy_source_warnings",
            ["strategy_source_has_finish_gatekeeper_step", "strategy_source_warnings"],
        ),
        (
            "strategy_source_execution_settings",
            [
                "default_strategy_role_execution_settings",
                "normalize_strategy_role_execution_settings",
                "strategy_role_uses_execution_snapshot",
            ],
        ),
        (
            "strategy_source_validation",
            ["normalize_strategy_source_identifier", "normalize_strategy_source_version"],
        ),
        (
            "strategy_source_prompt_assets",
            [
                "available_strategy_prompt_templates",
                "builtin_strategy_prompt_markdown",
                "load_strategy_prompt_file",
            ],
        ),
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

    for owner_module, names in ownership_groups:
        owner_source = owner_sources[owner_module]
        for name in names:
            assert f"def {name}" in owner_source
            assert f"def {name}" not in definitions_source
            assert f"definition_{name}" in facade_source
    for marker in old_facade_markers:
        assert marker not in facade_source
