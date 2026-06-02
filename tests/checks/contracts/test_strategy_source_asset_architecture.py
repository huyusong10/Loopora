from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _loopora_source(*parts: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / Path(*parts)).read_text(encoding="utf-8")


def test_asset_catalog_uses_strategy_source_boundary_for_strategy_templates() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    asset_catalog_source = (REPO_ROOT / "src" / "loopora" / "asset_catalog.py").read_text(encoding="utf-8")
    asset_catalog_resolution_source = (REPO_ROOT / "src" / "loopora" / "asset_catalog_orchestration_resolution.py").read_text(encoding="utf-8")
    asset_catalog_builtins_source = (REPO_ROOT / "src" / "loopora" / "asset_catalog_builtins.py").read_text(encoding="utf-8")
    service_app_source = (REPO_ROOT / "src" / "loopora" / "service_app.py").read_text(encoding="utf-8")
    assert "def strategy_source_preset_names" in strategy_source_source
    assert "def strategy_source_preset_copy" in strategy_source_source
    assert "def default_strategy_role_execution_settings" in strategy_source_source
    assert "def normalize_strategy_prompt_ref" in strategy_source_source
    assert "class StrategyTemplateAssetCatalog" in asset_catalog_source
    assert "WorkflowAssetCatalog = StrategyTemplateAssetCatalog" in asset_catalog_source
    assert "class WorkflowAssetCatalog" not in asset_catalog_source
    assert "StrategyTemplateAssetCatalog(repository)" in service_app_source
    assert "WorkflowAssetCatalog(repository)" not in service_app_source
    assert "from loopora.strategy_source import" in asset_catalog_source
    assert "from loopora.workflows import" not in asset_catalog_source
    assert "hydrate_strategy_role_snapshots(" in asset_catalog_resolution_source
    assert "_hydrate_workflow_role_snapshots" not in asset_catalog_source
    assert "strategy_source = build_preset_strategy_source(preset_name)" in asset_catalog_builtins_source
    assert "workflow = build_preset_strategy_source(preset_name)" not in asset_catalog_builtins_source
    assert "normalized_strategy_source = normalize_strategy_source" in asset_catalog_resolution_source
    assert "normalized_workflow" not in asset_catalog_source
    assert "hydrated_strategy_source" in asset_catalog_resolution_source
    assert "effective_strategy_source" in asset_catalog_source
    assert "effective_workflow" not in asset_catalog_source


def test_orchestration_asset_mutations_use_strategy_source_boundary_for_strategy_templates() -> None:
    asset_catalog_source = (REPO_ROOT / "src" / "loopora" / "asset_catalog.py").read_text(encoding="utf-8")
    asset_catalog_inputs_source = (REPO_ROOT / "src" / "loopora" / "asset_catalog_inputs.py").read_text(encoding="utf-8")
    service_orchestration_source = (REPO_ROOT / "src" / "loopora" / "service_orchestration_assets.py").read_text(
        encoding="utf-8"
    )

    assert "strategy_source: dict | None = None" in asset_catalog_source
    assert "strategy_source: dict | None = None" in service_orchestration_source
    assert "def _pop_strategy_source_payload" in asset_catalog_inputs_source
    assert "def _pop_strategy_source_field" in service_orchestration_source
    assert "payload_input.strategy_source" in asset_catalog_source
    assert "payload_input.workflow" not in asset_catalog_source
    assert all(marker in service_orchestration_source for marker in ("strategy_source=request.strategy_source", "strategy_source_from_record(previous_orchestration) or {}"))
    assert "workflow=request.workflow" not in service_orchestration_source
    assert "role_count, step_count = _strategy_source_counts(orchestration)" in service_orchestration_source


def test_bundle_control_summary_uses_strategy_source_boundary_for_loopfile_workflow_input() -> None:
    control_summary_source = _loopora_source("service_bundle_control_summary.py")
    control_diagnostics_source = _loopora_source("service_bundle_control_diagnostics.py")
    control_flow_source = _loopora_source("service_bundle_control_flow.py")
    control_traces_source = _loopora_source("service_bundle_control_traces.py")
    control_trace_mining_source = _loopora_source("service_bundle_control_trace_mining.py")

    assert 'strategy_source = dict(bundle.get("workflow") or {})' in control_summary_source
    assert 'workflow = dict(bundle.get("workflow") or {})' not in control_summary_source
    assert "strategy_flow_projection = build_bundle_strategy_flow_projection" in control_summary_source
    assert "def build_bundle_strategy_flow_projection" in control_flow_source
    assert "def _strategy_flow_projection" not in control_summary_source
    assert "def _workflow_projection" not in control_summary_source
    assert "def _strategy_flow_trace" in control_traces_source
    assert "def build_bundle_traceability_projection" in control_traces_source
    assert "def build_execution_strategy_trace" in control_trace_mining_source
    assert "def _workflow_trace" not in control_summary_source
    assert "from loopora.service_bundle_control_flow import" in control_summary_source
    assert "from loopora.service_bundle_control_traces import" in control_summary_source
    assert "from loopora.service_bundle_control_trace_mining import" in control_traces_source
    assert "from loopora.service_bundle_control_diagnostics import build_bundle_control_diagnostics" in control_summary_source
    assert "def build_bundle_diagnostic_step_contexts" in control_flow_source
    assert "def _diagnostic_step_contexts" not in control_summary_source
    assert "def build_bundle_control_diagnostics" in control_diagnostics_source
    assert "append_strategy_input_diagnostics" in control_diagnostics_source
    assert "def _append_workflow_input_diagnostics" not in control_diagnostics_source
    assert 'strategy_source = dict(context.get("strategy_source") or context.get("workflow") or {})' in control_traces_source


def test_bundle_graph_preflight_uses_strategy_source_for_template_role_refs() -> None:
    graph_preflight_source = (REPO_ROOT / "src" / "loopora" / "service_bundle_graph_preflight.py").read_text(
        encoding="utf-8"
    )

    assert "strategy_source_from_record(orchestration) or {}" in graph_preflight_source
    assert 'orchestration.get("workflow_json") or {}' not in graph_preflight_source
    assert "_strategy_source_role_definition_ids" in graph_preflight_source
    assert "_workflow_role_definition_ids" not in graph_preflight_source


def test_loopfile_bundle_uses_strategy_source_boundary_for_strategy_validation() -> None:
    strategy_source_source = _loopora_source("strategy_source.py")
    bundles_source = _loopora_source("bundles.py")
    bundle_semantic_lint_source = _loopora_source("bundle_semantic_lint.py")
    bundle_strategy_boundary_source = "\n".join(_loopora_source(path) for path in ("bundle_contract.py", "bundle_loop_settings.py", "bundle_role_definitions.py", "bundle_workflow_normalization.py"))

    assert "def normalize_strategy_source_identifier" in strategy_source_source
    assert "def normalize_strategy_source_controls" in strategy_source_source
    assert "def default_strategy_step_execution_settings" in strategy_source_source
    assert "from loopora.strategy_source import" in bundle_strategy_boundary_source
    assert "from loopora.workflows import" not in bundles_source + bundle_strategy_boundary_source
    assert "StrategySourceError" in bundle_strategy_boundary_source
    assert "from loopora.bundle_semantic_lint import" in bundles_source
    assert "def lint_alignment_bundle_semantics" not in bundles_source
    assert "def lint_alignment_bundle_semantics" in bundle_semantic_lint_source
    assert "def normalize_bundle" not in bundle_semantic_lint_source
    assert "from loopora.bundles import normalize_bundle" in bundle_semantic_lint_source
