from __future__ import annotations

from bundle_service_architecture_test_support import design_contracts_source, loopora_source


def test_bundle_yaml_facade_keeps_normalization_boundaries_split() -> None:
    bundles_source = loopora_source("bundles.py")
    contract_source = loopora_source("bundle_contract.py")
    loop_source = loopora_source("bundle_loop_settings.py")
    role_source = loopora_source("bundle_role_definitions.py")
    workflow_source = loopora_source("bundle_workflow_normalization.py")
    normalization_source = loopora_source("bundle_normalization.py")
    io_source = loopora_source("bundle_io.py")
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
    assert "def _normalize_bundle_role_definition" in role_source
    assert "def _normalize_bundle_role_definition" not in bundles_source
    assert "def _normalize_bundle_workflow_step_payload" in workflow_source
    assert "def _normalize_bundle_workflow_step_payload" not in bundles_source
    assert "def normalize_bundle" in normalization_source
    assert "def normalize_bundle" not in bundles_source
    for marker in ("def read_bundle_file_text", "def load_bundle_text", "def bundle_to_yaml"):
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
