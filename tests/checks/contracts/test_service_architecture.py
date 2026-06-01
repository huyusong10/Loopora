from __future__ import annotations

from pathlib import Path
import ast

import loopora.service as service_module
from loopora.db import LooporaRepository
from loopora.service import LooporaService
from loopora.service_app import (
    AgentNativeService,
    AlignmentService,
    AssetRegistryService,
    BundleService,
    LooporaAppServices,
    ProjectionService,
    RunService,
)
from loopora.settings import AppSettings


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVICE_PRIVATE_IMPORT_ALLOWLIST: set[tuple[str, str, str]] = set()


def _loopora_source(*parts: str) -> str:
    return (REPO_ROOT / "src" / "loopora" / Path(*parts)).read_text(encoding="utf-8")


def test_loopora_service_is_composition_facade(tmp_path: Path) -> None:
    repository = LooporaRepository(tmp_path / "app.db")
    service = LooporaService(repository=repository, settings=AppSettings())

    assert LooporaService.__bases__ == (object,)
    assert isinstance(service.app_services, LooporaAppServices)
    assert isinstance(service.app_services.alignment, AlignmentService)
    assert isinstance(service.app_services.bundle, BundleService)
    assert isinstance(service.app_services.run, RunService)
    assert isinstance(service.app_services.agent_native, AgentNativeService)
    assert isinstance(service.app_services.asset_registry, AssetRegistryService)
    assert isinstance(service.app_services.projection, ProjectionService)
    assert service.repository is repository
    assert callable(service.start_agent_loop)
    assert callable(service.app_services.agent_native.submit_step)
    assert callable(service.app_services.run.observation_snapshot)
    assert callable(service.app_services.projection.web_run_detail)


def test_public_service_module_does_not_import_legacy_mixins() -> None:
    source = Path(service_module.__file__).read_text(encoding="utf-8")
    service_app_source = _loopora_source("service_app.py")
    service_alignment_source = _loopora_source("service_alignment.py")
    alignment_status_source = _loopora_source("service_alignment_status.py")
    web_alignment_event_api_source = _loopora_source("web_alignment_event_api.py")

    assert "ServiceAlignmentMixin" not in source
    assert "ServiceLegacyExecutionMixin" not in source
    assert "ServiceWorkflowExecutionMixin" not in source
    assert "ServiceRunnerExecutionMixin" not in source
    assert "ServiceLegacyExecutionMixin" not in service_app_source
    assert "ServiceWorkflowExecutionMixin" not in service_app_source
    assert "service_legacy_execution" not in service_app_source
    assert "ServiceAlignmentLegacyMixin" not in service_alignment_source
    assert "ensure_alignment_session_layout" in (REPO_ROOT / "src" / "loopora" / "service_alignment_session_layout_context.py").read_text(encoding="utf-8")
    assert "ALIGNMENT_ACTIVE_STATUSES =" not in service_alignment_source
    assert "ALIGNMENT_ACTIVE_STATUSES =" in alignment_status_source
    assert "from loopora.service_alignment_status import ALIGNMENT_ACTIVE_STATUSES" in web_alignment_event_api_source


def test_component_services_expose_explicit_boundary_methods() -> None:
    component_methods = {
        AlignmentService: {"get_workdir_context", "resolve_context", "list_sessions"},
        BundleService: {"list_exchange_items", "import_text", "preview_text"},
        RunService: {"get_run", "start_run", "start_run_async", "stop_run", "stream_events", "observation_snapshot"},
        AgentNativeService: {"start_loop", "prepare_run", "claim_step", "submit_step", "entry_loop_start_projection"},
        AssetRegistryService: {"local_diagnostics"},
        ProjectionService: {"web_run_detail"},
    }

    for service_class, method_names in component_methods.items():
        explicit = {name for name, value in service_class.__dict__.items() if callable(value) and not name.startswith("_")}
        assert method_names <= explicit


def test_component_services_do_not_expose_runtime_pass_through(tmp_path: Path) -> None:
    service = LooporaService(repository=LooporaRepository(tmp_path / "app.db"), settings=AppSettings())

    assert callable(service.start_agent_loop)
    assert "__getattr__" in LooporaService.__dict__
    for component in (
        service.app_services.alignment,
        service.app_services.bundle,
        service.app_services.run,
        service.app_services.agent_native,
        service.app_services.asset_registry,
        service.app_services.projection,
    ):
        assert "__getattr__" not in type(component).__dict__

    assert not hasattr(service.app_services.run, "start_agent_loop")
    assert not hasattr(service.app_services.agent_native, "start_run")
    assert not hasattr(service.app_services.projection, "get_runtime_activity")


def test_service_private_helper_imports_do_not_grow_without_inventory() -> None:
    assert not SERVICE_PRIVATE_IMPORT_ALLOWLIST
    offenders: list[tuple[str, str, str]] = []
    for path in sorted((REPO_ROOT / "src" / "loopora").glob("service*.py")):
        relative = str(path.relative_to(REPO_ROOT))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module or not node.module.startswith("loopora.service"):
                continue
            offenders.extend(
                (relative, node.module, alias.name)
                for alias in node.names
                if alias.name.startswith("_") and (relative, node.module, alias.name) not in SERVICE_PRIVATE_IMPORT_ALLOWLIST
            )

    assert offenders == []


def test_service_boundary_inventory_documents_private_import_retirement() -> None:
    inventory = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "Service-to-service private helper imports are retired" in inventory
    assert "LooporaServiceRuntime" in inventory
    assert "AgentNativeService" in inventory
    assert "ProjectionService" in inventory
    assert "AlignmentService" in inventory
    assert "service_alignment_context_factory.py" in inventory and "service_alignment.py" in inventory
    assert all(name in inventory for name in ("alignment_traceability_terms.py", "alignment_traceability_categories.py"))
    assert "remaining extraction target is small compatibility helpers in `service_alignment.py`" not in inventory


def test_service_alignment_facade_only_exposes_public_delegates_and_context_factory() -> None:
    source = _loopora_source("service_alignment.py")
    tree = ast.parse(source)
    top_level_functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    mixin = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ServiceAlignmentMixin")
    private_methods = [node.name for node in mixin.body if isinstance(node, ast.FunctionDef) and node.name.startswith("_")]

    assert top_level_functions == []
    assert private_methods == ["_alignment_context_factory"]
    assert "explicit public compatibility delegates plus the context-factory hook" in (
        REPO_ROOT / "design" / "contracts.md"
    ).read_text(encoding="utf-8")


def test_agent_native_uses_engine_runtime_context_not_workflow_private_types() -> None:
    source = "".join(map(_loopora_source, ("service_agent_native.py", "service_agent_native_claim.py", "service_agent_native_iteration.py", "agent_native_claim_runtime_step.py")))
    runner_step_runtime_source = _loopora_source("runner_step_runtime.py")
    runner_run_requests_source = _loopora_source("runner_run_requests.py")
    runner_support_requests_source = _loopora_source("runner_support_requests.py")
    service_runner_failure_source = _loopora_source("service_runner_failure_handling.py")
    service_runner_iteration_source = _loopora_source("service_runner_iteration_state.py")
    service_runner_step_runtime_source = _loopora_source("service_runner_step_runtime.py")
    service_runner_support_source = _loopora_source("service_runner_support.py")

    assert "loopora.service_runner_execution" not in source
    assert "loopora.service_runner_failure_handling" not in source
    assert "loopora.service_runner_iteration_state" not in source
    assert "loopora.service_workflow_runtime" not in source
    assert "loopora.service_runner_step_runtime" not in source
    assert "loopora.service_runner_support" not in source
    assert "loopora.engine.workflow_runtime" not in source
    assert "loopora.engine.runner_runtime" not in source
    assert "loopora.engine.runner_context" in source
    assert "loopora.engine.workflow_context" not in source
    assert "loopora.runner_run_requests" in source
    assert "loopora.workflow_run_requests" not in source
    assert "loopora.runner_support_requests" in source
    assert "loopora.workflow_support_requests" not in source
    assert "loopora.runner_step_runtime" in source
    assert "loopora.workflow_step_runtime" not in source
    assert "_prepare_runner_step_request" not in source
    assert "prepare_runner_step_request" in source
    assert "prepare_workflow_step_request" not in source
    assert "RunnerRunContext" in source
    assert "RunnerIterationState" in source
    assert "WorkflowRunContext" not in source
    assert "WorkflowIterationState" not in source
    assert "class RunnerExhaustionRequest" in runner_run_requests_source
    assert "class RunnerIterationCheckpointRequest" in runner_run_requests_source
    assert "from loopora.runner_run_requests import RunnerExhaustionRequest" in service_runner_failure_source
    assert "from loopora.runner_run_requests import RunnerIterationCheckpointRequest" in service_runner_iteration_source
    assert "class StepOutputNormalizationRequest" in runner_support_requests_source
    assert "class RunnerSummaryRequest" in runner_support_requests_source
    assert "strategy_source: dict" in runner_support_requests_source
    assert "workflow: dict" not in runner_support_requests_source
    assert "from loopora.runner_support_requests import" in service_runner_support_source
    assert "WorkflowSummaryRequest" not in service_runner_support_source
    assert "class RunnerStepRuntimeRequest" in runner_step_runtime_source
    assert "from loopora.runner_step_runtime import RunnerStepRuntimeRequest" in service_runner_step_runtime_source
    assert "class ServiceRunnerStepRuntimeMixin" in service_runner_step_runtime_source
    assert "ServiceWorkflowRuntimeMixin" not in service_runner_step_runtime_source
    assert "WorkflowStepRuntimeRequest" not in service_runner_step_runtime_source
    assert "def prepare_runner_step_request" in service_runner_step_runtime_source
    assert "def _prepare_runner_step_request" not in service_runner_step_runtime_source


def test_context_flow_delegates_schemas_and_prompt_contracts() -> None:
    import loopora.context_flow as context_flow
    import loopora.context_prompt_contracts as context_prompt_contracts
    import loopora.context_schemas as context_schemas

    context_flow_source = _loopora_source("context_flow.py")
    context_prompt_contracts_source = _loopora_source("context_prompt_contracts.py")
    context_schemas_source = _loopora_source("context_schemas.py")
    context_schema_boundary_source = _loopora_source("context_schema_shared.py") + _loopora_source("context_schema_step_instruction.py")
    context_schema_boundary_source += _loopora_source("context_schema_iteration_state.py") + _loopora_source("context_schema_runtime.py")
    headless_prompt_source = _loopora_source("headless_prompt.py")
    assert context_flow.STEP_INSTRUCTION_CONTEXT_SCHEMA is context_schemas.STEP_INSTRUCTION_CONTEXT_SCHEMA
    assert context_flow.ITERATION_SUMMARY_SCHEMA is context_schemas.ITERATION_SUMMARY_SCHEMA
    assert context_flow.output_contract_prompt is context_prompt_contracts.output_contract_prompt
    assert context_flow.system_prompt_prefix is context_prompt_contracts.system_prompt_prefix
    assert "STEP_INSTRUCTION_CONTEXT_SCHEMA = {" not in context_flow_source
    assert "ITERATION_SUMMARY_SCHEMA = {" not in context_flow_source
    assert all(marker in context_schema_boundary_source for marker in ("STEP_INSTRUCTION_CONTEXT_SCHEMA = {", "ITERATION_SUMMARY_SCHEMA = {"))
    assert all(marker in context_schemas_source for marker in ("from loopora.context_schema_runtime import", "from loopora.context_schema_shared import"))
    assert "def output_contract_prompt" not in context_flow_source
    assert "def system_prompt_prefix" not in context_flow_source
    assert "def output_contract_prompt" in context_prompt_contracts_source
    assert "def system_prompt_prefix" in context_prompt_contracts_source
    assert "from loopora.context_prompt_contracts import" in headless_prompt_source
    assert "def build_step_instruction_context" in context_flow_source
    assert "def build_step_instruction_context" not in context_schemas_source


def test_context_flow_delegates_prompt_sections() -> None:
    import loopora.context_flow as context_flow
    import loopora.context_prompt_sections as context_prompt_sections

    context_flow_source = _loopora_source("context_flow.py")
    context_prompt_sections_source = _loopora_source("context_prompt_sections.py")
    headless_prompt_source = _loopora_source("headless_prompt.py")

    assert context_flow.render_iteration_section is context_prompt_sections.render_iteration_section
    assert context_flow.render_evidence_section is context_prompt_sections.render_evidence_section
    assert context_flow.render_artifact_refs is context_prompt_sections.render_artifact_refs
    assert "def render_iteration_section" not in context_flow_source
    assert "def render_evidence_section" not in context_flow_source
    assert "def render_artifact_refs" not in context_flow_source
    assert "def render_iteration_section" in context_prompt_sections_source
    assert "def render_evidence_section" in context_prompt_sections_source
    assert "def render_artifact_refs" in context_prompt_sections_source
    assert "from loopora.context_value_helpers import clean_text as _clean_text" in context_prompt_sections_source
    assert "from loopora.context_prompt_sections import" in headless_prompt_source


def test_context_flow_delegates_run_contract_and_step_result_projections() -> None:
    import loopora.context_contract_snapshot as context_contract_snapshot
    import loopora.context_flow as context_flow
    import loopora.context_step_results as context_step_results

    context_contract_snapshot_source = _loopora_source("context_contract_snapshot.py")
    context_flow_source = _loopora_source("context_flow.py")
    context_step_results_source = _loopora_source("context_step_results.py")
    service_runner_step_artifacts_source = _loopora_source("service_runner_step_artifacts.py")

    assert context_flow.RunContractSnapshotRequest is context_contract_snapshot.RunContractSnapshotRequest
    assert context_flow.build_run_contract_snapshot is context_contract_snapshot.build_run_contract_snapshot
    assert context_flow.StepResultContext is context_step_results.StepResultContext
    assert context_flow.build_step_handoff is context_step_results.build_step_handoff
    assert context_flow.evidence_entry_id is context_step_results.evidence_entry_id
    assert "class RunContractSnapshotRequest" not in context_flow_source
    assert "class RunContractSnapshotRequest" in context_contract_snapshot_source
    assert "class StepResultContext" not in context_flow_source
    assert "def build_step_handoff" not in context_flow_source
    assert "def evidence_entry_id" not in context_flow_source
    assert "class StepResultContext" in context_step_results_source
    assert "def build_step_handoff" in context_step_results_source
    assert "def evidence_entry_id" in context_step_results_source
    assert "from loopora.context_step_results import" in service_runner_step_artifacts_source


def test_context_flow_delegates_iteration_summary_projection() -> None:
    import loopora.context_flow as context_flow
    import loopora.context_iteration_summary as context_iteration_summary

    context_flow_source = _loopora_source("context_flow.py")
    context_iteration_summary_source = _loopora_source("context_iteration_summary.py")
    service_runner_support_source = _loopora_source("service_runner_support.py")

    assert context_flow.IterationSummaryContext is context_iteration_summary.IterationSummaryContext
    assert context_flow.build_iteration_summary is context_iteration_summary.build_iteration_summary
    assert context_flow.derive_latest_state is context_iteration_summary.derive_latest_state
    assert "class IterationSummaryContext" not in context_flow_source
    assert "def build_iteration_summary" not in context_flow_source
    assert "def derive_latest_state" not in context_flow_source
    assert "class IterationSummaryContext" in context_iteration_summary_source
    assert "def build_iteration_summary" in context_iteration_summary_source
    assert "def derive_latest_state" in context_iteration_summary_source
    assert "from loopora.context_iteration_summary import" in service_runner_support_source


def test_run_contract_snapshot_request_uses_strategy_source_input() -> None:
    context_contract_snapshot_source = (REPO_ROOT / "src" / "loopora" / "context_contract_snapshot.py").read_text(
        encoding="utf-8"
    )
    context_flow_source = (REPO_ROOT / "src" / "loopora" / "context_flow.py").read_text(encoding="utf-8")
    registration_source = (REPO_ROOT / "src" / "loopora" / "service_run_registration.py").read_text(encoding="utf-8")

    assert "class RunContractSnapshotRequest" in context_contract_snapshot_source
    assert "strategy_source: dict" in context_contract_snapshot_source
    assert "    workflow: dict\n    prompt_files" not in context_contract_snapshot_source
    assert "_strategy_source_roles_with_prompt_files" in context_contract_snapshot_source
    assert "_strategy_source_roles_with_prompt_files" not in context_flow_source
    assert "_workflow_roles_with_prompt_files" not in context_contract_snapshot_source
    assert 'strategy_snapshot = run_contract.get("workflow")' in context_flow_source
    assert 'workflow_snapshot = run_contract.get("workflow")' not in context_flow_source and "StepContextPacket" not in context_flow_source
    assert "strategy_source=strategy_source" in context_contract_snapshot_source
    assert "strategy_source=strategy_snapshot" in context_flow_source
    assert "workflow=strategy_source" not in context_contract_snapshot_source
    assert "workflow=strategy_snapshot" not in context_flow_source
    assert "from loopora.context_contract_snapshot import RunContractSnapshotRequest, build_run_contract_snapshot" in _loopora_source("service_run_start.py") and "class LoopCreateRequest" in _loopora_source("service_loop_create_inputs.py")
    assert "class ResolvedLoopCreate" in registration_source
    assert "class LoopCreateRequest" not in registration_source and "class LoopDefinitionFiles" in registration_source
    assert "strategy_source: dict" in registration_source
    assert "workflow: dict\n\n\n@dataclass(frozen=True, kw_only=True)\nclass ResolvedLoopCreate" not in registration_source
    assert "workflow: dict\n\n\ndef _coerce_loop_create_request" not in registration_source
    assert "_validate_loop_completion_strategy_source" in registration_source and "def start_run" not in registration_source and "def start_run" in _loopora_source("service_run_start.py")
    assert "_validate_loop_completion_workflow" not in registration_source
    assert "strategy_source = self._normalized_strategy_source_from_record(loop)" in _loopora_source("service_run_start.py")
    assert 'workflow = loop.get("workflow_json")' not in registration_source + _loopora_source("service_run_start.py")


def test_runtime_uses_strategy_source_boundary_for_workflow_source_helpers() -> None:
    strategy_source_path = REPO_ROOT / "src" / "loopora" / "strategy_source.py"
    strategy_source_source = strategy_source_path.read_text(encoding="utf-8")
    service_source = (REPO_ROOT / "src" / "loopora" / "service.py").read_text(encoding="utf-8")
    service_app_source = (REPO_ROOT / "src" / "loopora" / "service_app.py").read_text(encoding="utf-8")
    service_asset_common_source = (REPO_ROOT / "src" / "loopora" / "service_asset_common.py").read_text(
        encoding="utf-8"
    )
    service_bundle_assets_source = (REPO_ROOT / "src" / "loopora" / "service_bundle_assets.py").read_text(
        encoding="utf-8"
    )
    service_bundle_export_source = _loopora_source("service_bundle_export.py")
    runner_execution_source = _loopora_source("service_runner_execution.py") + _loopora_source(
        "service_runner_context_preparation.py"
    )
    agent_native_context_source = (REPO_ROOT / "src" / "loopora" / "agent_native_runtime_context.py").read_text(
        encoding="utf-8"
    )
    registration_source = (REPO_ROOT / "src" / "loopora" / "service_run_registration.py").read_text(encoding="utf-8")
    loop_records_source = (REPO_ROOT / "src" / "loopora" / "service_loop_records.py").read_text(encoding="utf-8")
    step_runtime_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_runtime.py").read_text(
        encoding="utf-8"
    )
    runner_support_source = (REPO_ROOT / "src" / "loopora" / "service_runner_support.py").read_text(encoding="utf-8")

    assert strategy_source_path.exists()
    assert "StrategySourceError" in strategy_source_source
    assert "def normalize_strategy_source" in strategy_source_source
    assert "def strategy_source_has_finish_gatekeeper_step" in strategy_source_source
    assert "def build_preset_strategy_source" in strategy_source_source
    assert "def resolve_strategy_prompt_files" in strategy_source_source
    assert "def normalize_strategy_role_models" in strategy_source_source
    assert "LEGACY_STRATEGY_ROLE_BY_ARCHETYPE" in strategy_source_source
    assert "STRATEGY_SOURCE_ARCHETYPES" in strategy_source_source
    assert "STRATEGY_ROLE_EXECUTION_FIELDS" in strategy_source_source
    assert "STRATEGY_ROLE_POSTURE_FIELDS" in strategy_source_source
    assert "from loopora.strategy_source import" in service_source
    assert "from loopora.strategy_source import" in service_app_source
    assert "from loopora.strategy_source import" in service_asset_common_source
    assert "from loopora.strategy_source import" in service_bundle_export_source
    assert "from loopora.strategy_source import" in runner_execution_source
    assert "from loopora.strategy_source import" in agent_native_context_source
    assert "from loopora.strategy_source import" in registration_source
    assert "from loopora.strategy_source import" in loop_records_source
    assert "from loopora.strategy_source import" in runner_support_source
    assert "from loopora.strategy_source import" in step_runtime_source
    assert "from loopora.workflows import" not in service_source
    assert "from loopora.workflows import" not in service_app_source
    assert "from loopora.workflows import" not in service_asset_common_source
    assert "from loopora.workflows import" not in service_bundle_assets_source
    assert "from loopora.workflows import" not in service_bundle_export_source
    assert "from loopora.workflows import" not in runner_execution_source
    assert "from loopora.workflows import" not in agent_native_context_source
    assert "from loopora.workflows import" not in registration_source
    assert "from loopora.workflows import" not in loop_records_source
    assert "from loopora.workflows import" not in runner_support_source
    assert "from loopora.workflows import" not in step_runtime_source
    assert all(marker in loop_records_source for marker in ("_normalized_strategy_source_from_record", "_strategy_source_snapshot_from_record")) and "def _read_prompt_files" in _loopora_source("service_loop_prompt_files.py") and "def _read_prompt_files" not in loop_records_source
    assert "strategy_source_from_record(run)" in agent_native_context_source
    assert "strategy_source = self._strategy_source_snapshot_from_record(run)" in runner_execution_source
    assert "_normalized_workflow_from_record" not in loop_records_source


def test_strategy_source_definitions_own_legacy_workflow_format_implementation() -> None:
    strategy_source_source = _loopora_source("strategy_source.py")
    strategy_definitions_source = _loopora_source("strategy_source_definitions.py")
    strategy_controls_source = _loopora_source("strategy_source_controls.py")
    strategy_preset_catalog_source = _loopora_source("strategy_source_preset_catalog.py")
    strategy_presets_source = _loopora_source("strategy_source_presets.py")
    strategy_prompt_assets_source = _loopora_source("strategy_source_prompt_assets.py")
    strategy_roles_source = _loopora_source("strategy_source_roles.py")
    strategy_steps_source = _loopora_source("strategy_source_steps.py")
    strategy_warnings_source = _loopora_source("strategy_source_warnings.py")
    strategy_execution_source = _loopora_source("strategy_source_execution_settings.py")
    strategy_validation_source = _loopora_source("strategy_source_validation.py")
    strategy_errors_source = _loopora_source("strategy_source_errors.py")
    strategy_files_source = _loopora_source("strategy_source_files.py")
    strategy_normalization_source = _loopora_source("strategy_source_normalization.py")
    workflow_compat_source = _loopora_source("workflows.py")
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
        (_loopora_source("strategy_source_preset_specs.py"), "class StrategySourcePresetDefinitionSpec"),
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
        (workflow_compat_source, "from loopora.strategy_source_definitions import *"),
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
        (workflow_compat_source, "def normalize_workflow"),
    ]
    for source, marker in excluded_markers:
        assert marker not in source


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
    assert "class StrategyTemplateAssetCatalog" in asset_catalog_source and "WorkflowAssetCatalog = StrategyTemplateAssetCatalog" in asset_catalog_source
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
    assert "payload_input.strategy_source" in asset_catalog_source and "payload_input.workflow" not in asset_catalog_source
    assert all(marker in service_orchestration_source for marker in ("strategy_source=request.strategy_source", "strategy_source_from_record(previous_orchestration) or {}"))
    assert "workflow=request.workflow" not in service_orchestration_source
    assert "role_count, step_count = _strategy_source_counts(orchestration)" in service_orchestration_source


def test_compiler_sources_use_strategy_source_boundary_for_strategy_inputs() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    loop_compiler_source = (REPO_ROOT / "src" / "loopora" / "compiler" / "loop_compiler.py").read_text(
        encoding="utf-8"
    )
    specs_source = _loopora_source("specs.py")
    spec_markdown_source = _loopora_source("spec_markdown.py")
    cli_spec_commands_source = (REPO_ROOT / "src" / "loopora" / "cli_spec_commands.py").read_text(encoding="utf-8")
    web_spec_source = (REPO_ROOT / "src" / "loopora" / "web_spec_api.py").read_text(encoding="utf-8")
    web_loop_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_loop_pages.py").read_text(
        encoding="utf-8"
    )
    assert "def normalize_strategy_role_display_name" in strategy_source_source
    assert "from loopora.strategy_source import" in loop_compiler_source and "strategy_source_from_record(record)" in loop_compiler_source and 'record.get("workflow_json")' not in loop_compiler_source
    assert "from loopora.spec_markdown import" in specs_source and "from loopora.strategy_source import" in spec_markdown_source
    assert "from loopora.workflows import" not in loop_compiler_source
    assert "from loopora.workflows import" not in specs_source
    assert "def render_spec_template_for_strategy_source" in specs_source
    assert "def init_spec_file_for_strategy_source" in specs_source
    assert "strategy_source: dict[str, Any] | None = None" in specs_source
    assert "render_spec_template_for_strategy_source" in cli_spec_commands_source
    assert "init_spec_file_for_strategy_source" in cli_spec_commands_source
    assert "render_spec_template(locale=locale, workflow=" not in cli_spec_commands_source
    assert "render_spec_template_for_strategy_source" in web_spec_source
    assert "init_spec_file_for_strategy_source" in web_spec_source
    assert "render_spec_template(locale=locale, workflow=" not in web_spec_source
    assert "render_spec_template_for_strategy_source" in web_loop_pages_source
    assert "_loopfile_strategy_source" in loop_compiler_source
    assert "_loopfile_strategy_workflow" not in loop_compiler_source
    assert 'strategy_source_payload = mapping(bundle.get("workflow"))' in loop_compiler_source
    assert 'workflow = mapping(bundle.get("workflow"))' not in loop_compiler_source


def test_run_takeaway_projection_uses_strategy_snapshot_for_contract_trace_inputs() -> None:
    control_trace_mining_source = _loopora_source("service_bundle_control_trace_mining.py")
    run_takeaways_source = _loopora_source("run_takeaways.py")
    common_source = _loopora_source("run_takeaway_common.py")
    evidence_source = _loopora_source("run_takeaway_evidence.py")
    iterations_source = _loopora_source("run_takeaway_iterations.py")
    judgment_source = _loopora_source("run_takeaway_judgment.py")
    legacy_source = _loopora_source("run_takeaway_legacy.py")

    assert "strategy_source: object = None" in control_trace_mining_source
    assert "from loopora.service_bundle_control_trace_mining import" in judgment_source and "service_bundle_control_summary" not in judgment_source
    assert 'strategy_snapshot = raw.get("workflow")' in judgment_source
    assert 'workflow = raw.get("workflow")' not in judgment_source
    assert "strategy_source=strategy_snapshot" in judgment_source
    assert "workflow=strategy_snapshot" not in judgment_source
    assert "from loopora.run_takeaway_common import" in run_takeaways_source
    assert "from loopora.run_takeaway_evidence import" in run_takeaways_source
    assert "from loopora.run_takeaway_iterations import" in run_takeaways_source
    assert "from loopora.run_takeaway_judgment import" in run_takeaways_source
    assert "from loopora.run_takeaway_legacy import build_legacy_iteration_takeaway" in run_takeaways_source
    assert "def display_iter" in common_source and "def clean_takeaway_text" in common_source
    assert "def build_evidence_coverage" in evidence_source and "def normalize_evidence_coverage_payload" in evidence_source
    assert "def build_structured_iteration_takeaways" in iterations_source and "def build_role_takeaway_from_handoff" in iterations_source
    assert "def build_judgment_contract" in judgment_source and "def normalize_judgment_contract_payload" in judgment_source
    assert "def build_legacy_iteration_takeaway" in legacy_source
    assert "def display_iter" not in run_takeaways_source
    assert "def build_evidence_coverage" not in run_takeaways_source
    assert "def build_structured_iteration_takeaways" not in run_takeaways_source
    assert "def build_judgment_contract" not in run_takeaways_source
    assert "def build_legacy_iteration_takeaway" not in run_takeaways_source
    for source_name in [
            "agent_entry_run_projection.py",
            "agent_native_judgment_contract.py",
            "agent_native_task_proof.py",
            "cli_run_contract_output.py",
            "service_alignment_run_source_projection.py",
        ]:
        source = _loopora_source(source_name)
        assert "from loopora.run_takeaway_judgment import build_judgment_contract" in source
        assert "from loopora.run_takeaways import build_judgment_contract" not in source
    web_overviews_source = _loopora_source("web_overviews.py")
    assert "from loopora.run_takeaway_common import" in web_overviews_source
    assert "from loopora.run_takeaway_evidence import build_evidence_coverage" in web_overviews_source


def test_run_lifecycle_delegates_agent_current_step_projection() -> None:
    lifecycle_source = _loopora_source("service_run_lifecycle.py")
    projection_source = _loopora_source("service_run_current_step_projection.py")
    acceptance_source = _loopora_source("service_run_acceptance.py") + _loopora_source("service_run_acceptance_evidence.py")

    assert "from loopora.service_run_current_step_projection import current_agent_step_projection" in _loopora_source("service_run_observation.py")
    assert "from loopora.service_run_acceptance import ServiceRunAcceptanceMixin" in lifecycle_source
    assert "agent_native_active_step_view" not in lifecycle_source
    assert "def current_agent_step_projection" in projection_source
    assert "agent_native_active_step_view" in projection_source
    assert "def run_acceptance_evidence_payload_from_takeaways" in acceptance_source
    assert "def _acceptance_judgment_summary" not in lifecycle_source


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


def test_web_input_projection_uses_strategy_source_boundary_for_strategy_forms() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    web_inputs_source = (REPO_ROOT / "src" / "loopora" / "web_inputs.py").read_text(encoding="utf-8")
    web_strategy_inputs_source = (REPO_ROOT / "src" / "loopora" / "web_strategy_inputs.py").read_text(
        encoding="utf-8"
    )
    web_loop_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_loop_pages.py").read_text(
        encoding="utf-8"
    )
    web_spec_source = (REPO_ROOT / "src" / "loopora" / "web_spec_api.py").read_text(encoding="utf-8")

    assert "def builtin_strategy_prompt_markdown_by_locale" in strategy_source_source
    assert "def normalize_strategy_prompt_locale" in strategy_source_source
    assert "from loopora.strategy_source import" not in web_inputs_source
    assert "from loopora.strategy_source import" in web_strategy_inputs_source
    assert "from loopora.workflows import" not in web_strategy_inputs_source
    assert "SpecTemplateStrategyCandidate" in web_strategy_inputs_source
    assert "SpecTemplateWorkflowCandidate" not in web_strategy_inputs_source
    assert "def _strategy_source_from_mapping" in web_strategy_inputs_source
    assert "def _workflow_from_mapping" not in web_strategy_inputs_source
    assert "def _strategy_source_for_spec_template" in web_strategy_inputs_source
    assert "def _workflow_for_spec_template" not in web_strategy_inputs_source
    assert "strategy_source = build_preset_strategy_source(preset_name)" in web_strategy_inputs_source
    assert "workflow = build_preset_strategy_source(preset_name)" not in web_strategy_inputs_source
    assert "strategy_source = strategy_source_from_record(orchestration) or {}" in web_strategy_inputs_source
    assert "workflow = dict(orchestration.get(\"workflow_json\") or {})" not in web_strategy_inputs_source
    assert "from loopora.web_strategy_inputs import" in web_inputs_source
    assert "_strategy_source_for_spec_template" in web_loop_pages_source
    assert "_workflow_for_spec_template" not in web_loop_pages_source
    assert "_strategy_source_for_spec_template" in web_spec_source
    assert "_workflow_for_spec_template" not in web_spec_source


def test_web_page_projections_use_strategy_source_boundary_for_strategy_display() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    web_overviews_source = (REPO_ROOT / "src" / "loopora" / "web_overviews.py").read_text(encoding="utf-8")
    web_projection_source = (REPO_ROOT / "src" / "loopora" / "web_projection.py").read_text(encoding="utf-8")
    web_route_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_loop_run_pages.py").read_text(encoding="utf-8")
    loop_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_loop_pages.py").read_text(
        encoding="utf-8"
    )

    assert "def available_strategy_prompt_templates" in strategy_source_source and "def strategy_source_from_record" in strategy_source_source
    assert "from loopora.strategy_source import" in web_projection_source and "strategy_source_from_record" in web_projection_source and "from loopora.strategy_source import" in loop_pages_source
    assert "from loopora.workflows import" not in "\n".join([web_overviews_source, web_projection_source, loop_pages_source])
    assert all(marker in web_overviews_source for marker in ("def _strategy_role_executor_summary", "def _overview_strategy_source", "strategy_source_from_record"))
    assert all(marker not in web_overviews_source for marker in ("def _workflow_role_executor_summary", 'strategy_source = loop.get("workflow_json") or {}', 'workflow = loop.get("workflow_json") or {}'))
    assert "def web_run_detail_progress_stages" in web_projection_source
    assert all(marker in web_route_pages_source for marker in ("_strategy_role_executor_summary", "web_projection = ctx.svc().app_services.projection.web_run_detail(run)", '"progress_stages": web_projection["progress_stages"]'))
    assert all(marker not in web_route_pages_source for marker in ("_workflow_role_executor_summary", "_progress_stage_seed"))


def test_web_editor_and_form_routes_use_strategy_source_boundary_for_strategy_validation() -> None:
    spec_api_source = (REPO_ROOT / "src" / "loopora" / "web_spec_api.py").read_text(encoding="utf-8")
    forms_source = (REPO_ROOT / "src" / "loopora" / "web_route_forms.py").read_text(encoding="utf-8")
    errors_source = (REPO_ROOT / "src" / "loopora" / "web_route_errors.py").read_text(encoding="utf-8")

    assert "from loopora.strategy_source import" in spec_api_source
    assert "from loopora.strategy_source import" in forms_source
    assert "from loopora.strategy_source import" in errors_source
    assert "from loopora.workflows import" not in spec_api_source
    assert "from loopora.workflows import" not in forms_source
    assert "from loopora.workflows import" not in errors_source
    assert "_role_note_sections_from_strategy_source" in spec_api_source
    assert "_role_note_sections_from_workflow" not in spec_api_source
    assert "strategy source validation error" in errors_source


def test_strategy_source_is_the_only_production_legacy_workflow_import_boundary() -> None:
    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "src" / "loopora").rglob("*.py")):
        if path.name == "strategy_source.py":
            continue
        source = path.read_text(encoding="utf-8")
        if "from loopora.workflows import" in source:
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_cli_projections_use_strategy_source_boundary_for_strategy_assets() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    cli_prompt_source = (REPO_ROOT / "src" / "loopora" / "cli_prompt_commands.py").read_text(encoding="utf-8")
    cli_options_source = (REPO_ROOT / "src" / "loopora" / "cli_options.py").read_text(encoding="utf-8")
    cli_spec_source = (REPO_ROOT / "src" / "loopora" / "cli_spec_support.py").read_text(encoding="utf-8")
    cli_strategy_path = REPO_ROOT / "src" / "loopora" / "cli_strategy_source_support.py"
    cli_strategy_source = cli_strategy_path.read_text(encoding="utf-8")

    assert "def load_strategy_source_file" in strategy_source_source
    assert "STRATEGY_PROMPT_FILES" in strategy_source_source
    assert cli_strategy_path.exists()
    assert not (REPO_ROOT / "src" / "loopora" / "cli_workflow_support.py").exists()
    assert "from loopora.strategy_source import" in cli_prompt_source
    assert "from loopora.strategy_source import" in cli_options_source
    assert "from loopora.strategy_source import" in cli_spec_source
    assert "from loopora.strategy_source import" in cli_strategy_source
    assert "StrategyPresetOption" in cli_options_source
    assert "--strategy-preset" in cli_options_source
    assert "StrategyFileOption" in cli_options_source
    assert "--strategy-file" in cli_options_source
    assert "resolve_spec_template_strategy_source" in cli_spec_source
    assert "role_note_sections_for_strategy_source" in cli_spec_source
    assert "resolve_spec_template_workflow" not in cli_spec_source
    assert "role_note_sections_for_workflow" not in cli_spec_source
    assert "resolve_strategy_source_bundle" in cli_strategy_source
    assert "strategy_source_bundle_from_entity" in cli_strategy_source
    assert "resolve_workflow_bundle" not in cli_strategy_source
    assert "workflow_bundle_from_entity" not in cli_strategy_source
    assert "workflow_preset:" not in cli_strategy_source
    assert "workflow_file:" not in cli_strategy_source


def test_agent_native_control_policy_uses_strategy_boundary() -> None:
    agent_controls_source = (REPO_ROOT / "src" / "loopora" / "agent_native_controls.py").read_text(encoding="utf-8")

    assert (REPO_ROOT / "src" / "loopora" / "strategy_controls.py").exists()
    assert not (REPO_ROOT / "src" / "loopora" / "service_workflow_controls.py").exists()
    assert "from loopora.strategy_controls import" in agent_controls_source
    assert "loopora.service_workflow_controls" not in agent_controls_source
    assert "WorkflowControl" not in agent_controls_source
