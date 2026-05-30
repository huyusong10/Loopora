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
SERVICE_PRIVATE_IMPORT_ALLOWLIST = {
    ("src/loopora/service.py", "loopora.service_app", "_LooporaServiceRuntime"),
    ("src/loopora/service_agent_native.py", "loopora.service_agent_native_contracts", "_agent_native_actionable_blocking_item"),
    ("src/loopora/service_agent_native.py", "loopora.service_agent_native_contracts", "_agent_native_actionable_repair_next_action"),
    ("src/loopora/service_agent_native.py", "loopora.service_agent_native_contracts", "_agent_native_submit_command"),
    ("src/loopora/service_agent_native.py", "loopora.service_agent_native_contracts", "_agent_native_unknown_evidence_refs"),
    ("src/loopora/service_bundle_assets.py", "loopora.service_asset_common", "_normalize_role_models"),
    ("src/loopora/service_loop_records.py", "loopora.service_asset_common", "_normalize_role_models"),
    ("src/loopora/service_run_registration.py", "loopora.service_asset_common", "_normalize_role_models"),
}


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
    service_app_source = (REPO_ROOT / "src" / "loopora" / "service_app.py").read_text(encoding="utf-8")

    assert "ServiceAlignmentMixin" not in source
    assert "ServiceLegacyExecutionMixin" not in source
    assert "ServiceWorkflowExecutionMixin" not in source
    assert "ServiceRunnerExecutionMixin" not in source
    assert "ServiceLegacyExecutionMixin" not in service_app_source
    assert "ServiceWorkflowExecutionMixin" not in service_app_source
    assert "service_legacy_execution" not in service_app_source


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


def test_service_boundary_inventory_documents_transitional_private_imports() -> None:
    inventory = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "Existing private helper imports are treated as a temporary inventory" in inventory
    assert "AgentNativeService" in inventory
    assert "ProjectionService" in inventory
    assert "AlignmentService" in inventory
    assert "service_alignment.py" in inventory


def test_agent_native_uses_engine_runtime_context_not_workflow_private_types() -> None:
    source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    runner_step_runtime_source = (REPO_ROOT / "src" / "loopora" / "runner_step_runtime.py").read_text(
        encoding="utf-8"
    )
    runner_run_requests_source = (REPO_ROOT / "src" / "loopora" / "runner_run_requests.py").read_text(
        encoding="utf-8"
    )
    runner_support_requests_source = (REPO_ROOT / "src" / "loopora" / "runner_support_requests.py").read_text(
        encoding="utf-8"
    )
    service_runner_failure_source = (REPO_ROOT / "src" / "loopora" / "service_runner_failure_handling.py").read_text(
        encoding="utf-8"
    )
    service_runner_iteration_source = (REPO_ROOT / "src" / "loopora" / "service_runner_iteration_state.py").read_text(
        encoding="utf-8"
    )
    service_runner_step_runtime_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_runtime.py").read_text(
        encoding="utf-8"
    )
    service_runner_support_source = (REPO_ROOT / "src" / "loopora" / "service_runner_support.py").read_text(
        encoding="utf-8"
    )

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


def test_run_contract_snapshot_request_uses_strategy_source_input() -> None:
    context_flow_source = (REPO_ROOT / "src" / "loopora" / "context_flow.py").read_text(encoding="utf-8")
    registration_source = (REPO_ROOT / "src" / "loopora" / "service_run_registration.py").read_text(encoding="utf-8")

    assert "class RunContractSnapshotRequest" in context_flow_source
    assert "strategy_source: dict" in context_flow_source
    assert "    workflow: dict\n    prompt_files" not in context_flow_source
    assert "class ResolvedLoopCreate" in registration_source
    assert "class LoopDefinitionFiles" in registration_source
    assert "strategy_source: dict" in registration_source
    assert "workflow: dict\n\n\n@dataclass(frozen=True, kw_only=True)\nclass ResolvedLoopCreate" not in registration_source
    assert "workflow: dict\n\n\ndef _coerce_loop_create_request" not in registration_source
    assert "_validate_loop_completion_strategy_source" in registration_source
    assert "_validate_loop_completion_workflow" not in registration_source
    assert 'strategy_source = loop.get("workflow_json")' in registration_source
    assert 'workflow = loop.get("workflow_json")' not in registration_source


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
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
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
    assert "StrategySourceError = WorkflowError" in strategy_source_source
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
    assert "from loopora.strategy_source import" in service_bundle_assets_source
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
    assert "from loopora.workflows import" not in runner_execution_source
    assert "from loopora.workflows import" not in agent_native_context_source
    assert "from loopora.workflows import" not in registration_source
    assert "from loopora.workflows import" not in loop_records_source
    assert "from loopora.workflows import" not in runner_support_source
    assert "from loopora.workflows import" not in step_runtime_source
    assert "_normalized_strategy_source_from_record" in loop_records_source
    assert "_normalized_workflow_from_record" not in loop_records_source


def test_strategy_source_definitions_own_legacy_workflow_format_implementation() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    strategy_definitions_source = (REPO_ROOT / "src" / "loopora" / "strategy_source_definitions.py").read_text(
        encoding="utf-8"
    )
    workflow_compat_source = (REPO_ROOT / "src" / "loopora" / "workflows.py").read_text(encoding="utf-8")

    assert "from loopora.strategy_source_definitions import" in strategy_source_source
    assert "from loopora.workflows import" not in strategy_source_source
    assert "Strategy Source definitions" in strategy_definitions_source
    assert "Legacy workflow import compatibility" in workflow_compat_source
    assert "from loopora.strategy_source_definitions import *" in workflow_compat_source
    assert "def normalize_workflow" not in workflow_compat_source


def test_asset_catalog_uses_strategy_source_boundary_for_strategy_templates() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    asset_catalog_source = (REPO_ROOT / "src" / "loopora" / "asset_catalog.py").read_text(encoding="utf-8")

    assert "def strategy_source_preset_names" in strategy_source_source
    assert "def strategy_source_preset_copy" in strategy_source_source
    assert "def default_strategy_role_execution_settings" in strategy_source_source
    assert "def normalize_strategy_prompt_ref" in strategy_source_source
    assert "from loopora.strategy_source import" in asset_catalog_source
    assert "from loopora.workflows import" not in asset_catalog_source
    assert "_hydrate_strategy_role_snapshots" in asset_catalog_source
    assert "_hydrate_workflow_role_snapshots" not in asset_catalog_source


def test_compiler_sources_use_strategy_source_boundary_for_strategy_inputs() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    loop_compiler_source = (REPO_ROOT / "src" / "loopora" / "compiler" / "loop_compiler.py").read_text(
        encoding="utf-8"
    )
    specs_source = (REPO_ROOT / "src" / "loopora" / "specs.py").read_text(encoding="utf-8")

    assert "def normalize_strategy_role_display_name" in strategy_source_source
    assert "from loopora.strategy_source import" in loop_compiler_source
    assert "from loopora.strategy_source import" in specs_source
    assert "from loopora.workflows import" not in loop_compiler_source
    assert "from loopora.workflows import" not in specs_source
    assert "_loopfile_strategy_source" in loop_compiler_source
    assert "_loopfile_strategy_workflow" not in loop_compiler_source


def test_loopfile_bundle_uses_strategy_source_boundary_for_strategy_validation() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    bundles_source = (REPO_ROOT / "src" / "loopora" / "bundles.py").read_text(encoding="utf-8")

    assert "def normalize_strategy_source_identifier" in strategy_source_source
    assert "def normalize_strategy_source_controls" in strategy_source_source
    assert "def default_strategy_step_execution_settings" in strategy_source_source
    assert "from loopora.strategy_source import" in bundles_source
    assert "from loopora.workflows import" not in bundles_source
    assert "StrategySourceError" in bundles_source


def test_web_input_projection_uses_strategy_source_boundary_for_strategy_forms() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    web_inputs_source = (REPO_ROOT / "src" / "loopora" / "web_inputs.py").read_text(encoding="utf-8")

    assert "def builtin_strategy_prompt_markdown_by_locale" in strategy_source_source
    assert "def normalize_strategy_prompt_locale" in strategy_source_source
    assert "from loopora.strategy_source import" in web_inputs_source
    assert "from loopora.workflows import" not in web_inputs_source
    assert "SpecTemplateStrategyCandidate" in web_inputs_source
    assert "SpecTemplateWorkflowCandidate" not in web_inputs_source


def test_web_page_projections_use_strategy_source_boundary_for_strategy_display() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    web_overviews_source = (REPO_ROOT / "src" / "loopora" / "web_overviews.py").read_text(encoding="utf-8")
    loop_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_loop_pages.py").read_text(
        encoding="utf-8"
    )

    assert "def available_strategy_prompt_templates" in strategy_source_source
    assert "from loopora.strategy_source import" in web_overviews_source
    assert "from loopora.strategy_source import" in loop_pages_source
    assert "from loopora.workflows import" not in web_overviews_source
    assert "from loopora.workflows import" not in loop_pages_source


def test_web_editor_and_form_routes_use_strategy_source_boundary_for_strategy_validation() -> None:
    editor_source = (REPO_ROOT / "src" / "loopora" / "web_route_editor_api.py").read_text(encoding="utf-8")
    forms_source = (REPO_ROOT / "src" / "loopora" / "web_route_forms.py").read_text(encoding="utf-8")
    errors_source = (REPO_ROOT / "src" / "loopora" / "web_route_errors.py").read_text(encoding="utf-8")

    assert "from loopora.strategy_source import" in editor_source
    assert "from loopora.strategy_source import" in forms_source
    assert "from loopora.strategy_source import" in errors_source
    assert "from loopora.workflows import" not in editor_source
    assert "from loopora.workflows import" not in forms_source
    assert "from loopora.workflows import" not in errors_source
    assert "_role_note_sections_from_strategy_source" in editor_source
    assert "_role_note_sections_from_workflow" not in editor_source
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


def test_runner_support_boundary_is_runner_named() -> None:
    service_app_source = (REPO_ROOT / "src" / "loopora" / "service_app.py").read_text(encoding="utf-8")
    support_source = (REPO_ROOT / "src" / "loopora" / "service_runner_support.py").read_text(encoding="utf-8")

    assert not (REPO_ROOT / "src" / "loopora" / "service_workflow_support.py").exists()
    assert "from loopora.service_runner_support import ServiceRunnerSupportMixin" in service_app_source
    assert "ServiceWorkflowSupportMixin" not in service_app_source
    assert "class ServiceRunnerSupportMixin" in support_source
    assert "def _build_runner_summary" in support_source
    assert "def _build_runner_iteration_entry" in support_source
    assert "def _build_workflow_summary" not in support_source
    assert "def _build_workflow_iteration_entry" not in support_source


def test_runner_failure_boundary_is_runner_named() -> None:
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
    )
    failure_source = (REPO_ROOT / "src" / "loopora" / "service_runner_failure_handling.py").read_text(encoding="utf-8")

    assert not (REPO_ROOT / "src" / "loopora" / "service_workflow_failure_handling.py").exists()
    assert "from loopora.service_runner_failure_handling import ServiceRunnerFailureHandlingMixin" in runner_execution_source
    assert "ServiceWorkflowFailureHandlingMixin" not in runner_execution_source
    assert "class ServiceRunnerFailureHandlingMixin" in failure_source
    assert "def _handle_runner_exhaustion" in failure_source
    assert "def _handle_workflow_exhaustion" not in failure_source
    assert "def _handle_runner_execution_exception" in runner_execution_source
    assert "def _handle_workflow_execution_exception" not in runner_execution_source


def test_runner_execution_boundary_is_runner_named() -> None:
    service_app_source = (REPO_ROOT / "src" / "loopora" / "service_app.py").read_text(encoding="utf-8")
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
    )

    assert not (REPO_ROOT / "src" / "loopora" / "service_workflow_execution.py").exists()
    assert "from loopora.service_runner_execution import ServiceRunnerExecutionMixin" in service_app_source
    assert "ServiceWorkflowExecutionMixin" not in service_app_source
    assert "class ServiceRunnerExecutionMixin" in runner_execution_source
    assert "def _execute_runner_run" in runner_execution_source
    assert "def _run_runner_iteration" in runner_execution_source
    assert "def _run_runner_step_once" in runner_execution_source
    assert "class ServiceWorkflowExecutionMixin" not in runner_execution_source
    assert "def _execute_workflow_run" not in runner_execution_source
    assert "def _run_workflow_iteration" not in runner_execution_source
    assert "def _run_workflow_step_once" not in runner_execution_source


def test_runner_iteration_state_boundary_is_runner_named() -> None:
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    iteration_source = (REPO_ROOT / "src" / "loopora" / "service_runner_iteration_state.py").read_text(encoding="utf-8")
    workflow_iteration_path = REPO_ROOT / "src" / "loopora" / "service_workflow_iteration_state.py"

    assert not workflow_iteration_path.exists()
    assert "from loopora.service_runner_iteration_state import" in commit_source
    assert "RunnerGatekeeperSuccessRequest" in commit_source
    assert "_finish_runner_gatekeeper_success" in commit_source
    assert "WorkflowGatekeeperSuccessRequest" not in commit_source
    assert "_finish_workflow_gatekeeper_success" not in commit_source
    assert "class ServiceRunnerIterationStateMixin" in iteration_source
    assert "class WorkflowGatekeeperSuccessRequest" not in iteration_source
    assert "def _checkpoint_workflow_iteration_state" not in iteration_source


def test_runner_context_and_runtime_modules_are_runner_named() -> None:
    runner_context_source = (REPO_ROOT / "src" / "loopora" / "engine" / "runner_context.py").read_text(
        encoding="utf-8"
    )
    runner_runtime_source = (REPO_ROOT / "src" / "loopora" / "engine" / "runner_runtime.py").read_text(
        encoding="utf-8"
    )
    runner_execution_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(
        encoding="utf-8"
    )

    assert not (REPO_ROOT / "src" / "loopora" / "engine" / "workflow_context.py").exists()
    assert not (REPO_ROOT / "src" / "loopora" / "engine" / "workflow_runtime.py").exists()
    assert "class RunnerRunContext" in runner_context_source
    assert "class RunnerIterationState" in runner_context_source
    assert "strategy_source: dict" in runner_context_source
    assert "strategy_steps: list[dict]" in runner_context_source
    assert "strategy_controls: list[dict]" in runner_context_source
    assert "runner_started_at: float" in runner_context_source
    assert "workflow: dict" not in runner_context_source
    assert "workflow_steps: list[dict]" not in runner_context_source
    assert "workflow_controls: list[dict]" not in runner_context_source
    assert "workflow_started_at: float" not in runner_context_source
    assert "class RunnerRunProgress" in runner_runtime_source
    assert "class RunnerStepRunRequest" in runner_runtime_source
    assert "WorkflowRunProgress" not in runner_runtime_source
    assert "WorkflowStepRunRequest" not in runner_runtime_source
    assert "from loopora.engine.runner_context import RunnerIterationState, RunnerRunContext" in runner_runtime_source
    assert "loopora.engine.workflow_context" not in runner_runtime_source
    assert "from loopora.engine.runner_runtime import" in runner_execution_source
    assert "strategy_source: dict" in runner_execution_source
    assert "workflow: dict" not in runner_execution_source
    assert "WorkflowRunProgress" not in runner_execution_source
    assert "WorkflowStepRunRequest" not in runner_execution_source


def test_runner_execution_submits_steps_through_run_engine() -> None:
    source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")

    assert "RunEngineSubmitStepRequest" in source
    assert ".submit_step(" in source
    assert "RunEngineCommitStepRequest" not in source
    assert ".commit_step(" not in source


def test_services_use_runner_actor_factories_for_run_engine_boundaries() -> None:
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(encoding="utf-8")
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")

    assert "headless_runner_actor" in runner_source
    assert "agent_runner_actor" in agent_source
    assert 'ActorRef(kind="runner"' not in runner_source
    assert 'ActorRef(kind="agent"' not in agent_source


def test_services_use_engine_advance_policy_for_runner_step_selection() -> None:
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(encoding="utf-8")
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")

    assert "select_next_runner_step" in runner_source
    assert "select_next_runner_step" in agent_source
    assert "select_next_workflow_step" not in runner_source
    assert "select_next_workflow_step" not in agent_source
    assert "RunnerStepSelectionRequest" in runner_source
    assert "RunnerStepSelectionRequest" in agent_source


def test_services_ask_run_engine_to_freeze_runner_step_instructions() -> None:
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(encoding="utf-8")
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")

    assert "RunEngineClaimRunnerStepRequest" in runner_source
    assert "RunEngineClaimRunnerStepRequest" in agent_source
    assert "RunEngineClaimWorkflowStepRequest" not in runner_source
    assert "RunEngineClaimWorkflowStepRequest" not in agent_source
    assert ".claim_workflow_step(" not in runner_source
    assert ".claim_workflow_step(" not in agent_source
    assert "runner_step_instruction" not in runner_source
    assert "runner_step_instruction" not in agent_source
    assert "workflow_step_instruction" not in runner_source
    assert "workflow_step_instruction" not in agent_source


def test_agent_native_treats_active_step_state_as_projection_checked_cache() -> None:
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    projection_cache_source = (REPO_ROOT / "src" / "loopora" / "events" / "projection_cache.py").read_text(
        encoding="utf-8"
    )

    assert "agent_native_active_step_is_stale" in agent_source
    assert ".current_step_projection(" not in agent_source
    assert "current_step_projection_for_run" in agent_source
    assert 'kind="event_replayed_current_step"' in projection_cache_source
    assert "get_projection_record(projection_name, run_id)" in projection_cache_source


def test_agent_native_writes_active_step_cache_after_run_engine_claim() -> None:
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    claim_runtime_step = agent_source[
        agent_source.index("def _agent_native_claim_runtime_step")
        : agent_source.index("def submit_agent_native_step")
    ]

    assert claim_runtime_step.index(".claim_runner_step(") < claim_runtime_step.index('state["active_step"] = {')


def test_agent_native_uses_run_engine_runner_cursor_before_state_step_index() -> None:
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    agent_state_source = (REPO_ROOT / "src" / "loopora" / "agent_native_state.py").read_text(encoding="utf-8")
    agent_submit_flow_source = (REPO_ROOT / "src" / "loopora" / "agent_native_submit_flow.py").read_text(encoding="utf-8")

    assert ".runner_step_index(" in agent_source
    assert ".workflow_step_index(" not in agent_source
    assert "strategy_steps=context.strategy_steps" in agent_source
    assert "workflow_steps=context.strategy_steps" not in agent_source
    assert "strategy_steps=request.context.strategy_steps" in agent_submit_flow_source
    assert "workflow_steps=request.context.strategy_steps" not in agent_submit_flow_source
    assert "strategy_steps: list[dict[str, Any]]" in agent_state_source
    assert "workflow_steps: list[dict[str, Any]]" not in agent_state_source
    assert "fallback_step_index=int(state.get(\"step_index\") or 0)" in agent_source


def test_runner_execution_submits_step_before_recording_step_evidence() -> None:
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    iteration_source = (REPO_ROOT / "src" / "loopora" / "service_runner_iteration_state.py").read_text(encoding="utf-8")

    assert "RunEngineRecordStepEvidenceRequest" in commit_source
    assert ".record_step_evidence(" in commit_source
    assert commit_source.index(".submit_step(") < commit_source.index(".record_step_evidence(")
    assert "RunEngineAcceptEvidenceRequest" not in commit_source
    assert "RunEngineCoverageRecomputedRequest" not in commit_source
    assert ".accept_evidence(" not in commit_source
    assert ".recompute_coverage(" not in commit_source
    assert "RunEngineRecordStepEvidenceRequest" not in iteration_source
    assert ".record_step_evidence(" not in iteration_source


def test_run_finalization_uses_stable_verdict_engine_actor_factory() -> None:
    finalization_source = (REPO_ROOT / "src" / "loopora" / "service_run_finalization.py").read_text(encoding="utf-8")
    actors_source = (REPO_ROOT / "src" / "loopora" / "kernel" / "actors.py").read_text(encoding="utf-8")

    assert "ActorRef.verdict_engine()" in finalization_source
    assert 'ActorRef(kind="system", id="verdict-engine"' not in finalization_source
    assert "def verdict_engine" in actors_source
    assert 'id="verdict-engine"' in actors_source


def test_agent_and_headless_share_runner_step_commit_boundary() -> None:
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")
    runner_source = (REPO_ROOT / "src" / "loopora" / "service_runner_execution.py").read_text(encoding="utf-8")
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    artifacts_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_artifacts.py").read_text(encoding="utf-8")
    step_result_source = (REPO_ROOT / "src" / "loopora" / "engine" / "step_result.py").read_text(encoding="utf-8")

    assert "commit_runner_step_result" in agent_source
    assert "commit_runner_step_result" in runner_source
    assert "_commit_runner_step_result" not in agent_source
    assert "_commit_runner_step_result" not in runner_source
    assert "def commit_runner_step_result" in commit_source
    assert "class ServiceRunnerStepCommitMixin" in commit_source
    assert "class ServiceRunnerStepArtifactsMixin" in artifacts_source
    assert "runner_step_result" in commit_source
    assert "workflow_step_result" not in commit_source
    assert "class RunnerStepResultRequest" in step_result_source
    assert "WorkflowStepResultRequest" not in step_result_source
    assert "write_runner_step_result_artifacts" in commit_source
    assert "def write_runner_step_result_artifacts" in artifacts_source
    assert "_write_runner_step_result_artifacts" not in commit_source
    assert "_commit_workflow_step_result" not in agent_source
    assert "_commit_workflow_step_result" not in runner_source
    assert "_write_workflow_step_result" not in commit_source
