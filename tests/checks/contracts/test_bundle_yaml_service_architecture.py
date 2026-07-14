from __future__ import annotations

from bundle_service_architecture_test_support import REPO_ROOT, design_contracts_source, loopora_source


def test_bundle_yaml_facade_keeps_normalization_boundaries_split() -> None:
    bundles_source = loopora_source("bundles.py")
    contract_source = loopora_source("bundle_contract.py")
    loop_source = loopora_source("bundle_loop_settings.py")
    role_source = loopora_source("bundle_role_definitions.py")
    workflow_source = loopora_source("bundle_workflow_normalization.py")
    normalization_source = loopora_source("bundle_normalization.py")
    io_source = loopora_source("bundle_io.py")
    compose_validation_source = loopora_source("loop_compose_validation.py")
    contracts_source = design_contracts_source()

    assert "from loopora.bundle_contract import" in bundles_source
    assert "from loopora.bundle_io import" in bundles_source
    assert "from loopora.bundle_normalization import normalize_bundle" in bundles_source
    assert "class BundleError" in contract_source
    assert "class BundleError" not in bundles_source
    assert "def normalize_bundle_identifier" in contract_source
    assert "def normalize_bundle_identifier" not in bundles_source
    assert "def _normalize_bundle_loop_execution" in loop_source
    assert "def _normalize_bundle_loop_execution" not in bundles_source
    assert "normalize_loop_compose_execution_options" in loop_source
    assert "normalize_loop_compose_runtime_options" in loop_source
    assert "normalize_executor_kind" not in loop_source
    assert "coerce_integral_number" not in loop_source
    assert "def _normalize_bundle_role_definition" in role_source
    assert "def _normalize_bundle_role_definition" not in bundles_source
    assert "default_loop_role_execution_options" in role_source
    assert "normalize_executor_kind" not in role_source
    assert "from loopora.strategy_source import" not in compose_validation_source
    assert "from loopora.strategy_source_roles import normalize_strategy_role_models" in compose_validation_source
    assert "from loopora.strategy_source_presets import strategy_source_preset_names" in compose_validation_source
    assert "def _normalize_bundle_workflow_step_payload" in workflow_source
    assert "def _normalize_bundle_workflow_step_payload" not in bundles_source
    assert "def normalize_bundle" in normalization_source
    assert "def normalize_bundle" not in bundles_source
    for marker in ("def resolve_bundle_file_path", "def read_bundle_file_text", "def load_bundle_text", "def bundle_to_yaml"):
        assert marker in io_source
        assert marker not in bundles_source
    for marker in (
        "bundle_contract.py",
        "bundle_loop_settings.py",
        "bundle_role_definitions.py",
        "bundle_workflow_normalization.py",
        "bundle_normalization.py",
        "bundle_io.py",
    ):
        assert marker in contracts_source


def test_plan_file_file_path_normalization_stays_in_bundle_io() -> None:
    io_source = loopora_source("bundle_io.py")
    service_source = loopora_source("service_bundle_assets.py")
    recovery_source = loopora_source("web_bundle_import_recovery.py")
    service_boundaries = (REPO_ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "def resolve_bundle_file_path" in io_source
    assert "path.expanduser().resolve()" in io_source
    assert "resolve_bundle_file_path(path)" in service_source
    assert "resolve_bundle_file_path(path)" in recovery_source
    assert "Plan File file-path normalization lives in `bundle_io.resolve_bundle_file_path`" in service_boundaries


def test_bundle_semantic_lint_has_dedicated_rule_boundaries() -> None:
    lint_source = loopora_source("bundle_semantic_lint.py")
    bundle_source = loopora_source("bundle_semantic_bundle.py")
    generation_source = loopora_source("bundle_semantic_generation.py")
    spec_source = loopora_source("bundle_semantic_spec.py")
    text_source = loopora_source("bundle_semantic_text.py")
    role_source = loopora_source("bundle_semantic_roles.py")
    workflow_source = loopora_source("bundle_semantic_workflow.py")
    gatekeeper_source = loopora_source("bundle_semantic_workflow_gatekeeper.py")
    workflow_memory_source = loopora_source("bundle_semantic_workflow_memory.py")
    workflow_support_source = loopora_source("bundle_semantic_workflow_support.py")
    bundles_source = loopora_source("bundles.py")
    contracts_source = design_contracts_source()

    assert "def lint_alignment_bundle_semantics" in lint_source
    assert "def lint_alignment_bundle_generation_text" in generation_source
    assert "def lint_alignment_bundle_generation_text" not in lint_source
    assert "from loopora.bundle_semantic_generation import" in lint_source
    assert "from loopora.bundle_semantic_lint import" in bundles_source
    assert "from loopora.bundle_semantic_bundle import" in lint_source
    assert "from loopora.bundle_semantic_roles import" in lint_source
    assert "from loopora.bundle_semantic_spec import" in lint_source
    assert "from loopora.bundle_semantic_text import" not in lint_source
    assert "from loopora.bundle_semantic_text import" in bundle_source
    assert "from loopora.bundle_semantic_text import" in spec_source
    assert "from loopora.bundle_semantic_text import" in workflow_source
    assert "from loopora.bundle_semantic_workflow import" in lint_source
    assert "from loopora.bundle_semantic_workflow_gatekeeper import" in lint_source
    assert "from loopora.bundle_semantic_workflow_memory import" in lint_source
    assert "from loopora.bundle_semantic_workflow_support import" in lint_source
    for marker in ("def _semantic_text_mentions_personality_memory_antipattern", "def _semantic_text_mentions_workflow_judgment_flow"):
        assert marker in text_source
        assert marker not in lint_source
    assert "def _lint_alignment_collaboration_summary" in bundle_source
    assert "def _lint_alignment_collaboration_summary" not in lint_source
    assert "def _lint_alignment_spec_semantics" in spec_source
    assert "def _lint_alignment_spec_semantics" not in lint_source
    assert "def _lint_alignment_parallel_review_inputs" in workflow_source
    assert "def _lint_alignment_parallel_review_inputs" not in lint_source
    assert "def _lint_alignment_gatekeeper_semantics" in gatekeeper_source
    assert "def _lint_alignment_gatekeeper_semantics" not in workflow_source
    assert "def _lint_alignment_role_semantics" in role_source
    assert "def _lint_alignment_role_semantics" not in workflow_source
    assert "def _lint_alignment_iteration_memory_inputs" in workflow_memory_source
    assert "def _lint_alignment_iteration_memory_inputs" not in workflow_source
    assert "def _review_steps_since_latest_builder" in workflow_support_source
    assert "def _review_steps_since_latest_builder" not in workflow_source
    assert "bundle_semantic_*.py" in contracts_source
