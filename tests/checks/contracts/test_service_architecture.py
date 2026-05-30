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
    assert "ServiceLegacyExecutionMixin" not in service_app_source
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

    assert "loopora.service_workflow_execution" not in source
    assert "WorkflowRunContext" in source
    assert "WorkflowIterationState" in source


def test_workflow_execution_submits_steps_through_run_engine() -> None:
    source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")

    assert "RunEngineSubmitStepRequest" in source
    assert ".submit_step(" in source
    assert "RunEngineCommitStepRequest" not in source
    assert ".commit_step(" not in source


def test_services_use_runner_actor_factories_for_run_engine_boundaries() -> None:
    workflow_source = (REPO_ROOT / "src" / "loopora" / "service_workflow_execution.py").read_text(encoding="utf-8")
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")

    assert "headless_runner_actor" in workflow_source
    assert "agent_runner_actor" in agent_source
    assert 'ActorRef(kind="runner"' not in workflow_source
    assert 'ActorRef(kind="agent"' not in agent_source


def test_services_use_engine_advance_policy_for_workflow_step_selection() -> None:
    workflow_source = (REPO_ROOT / "src" / "loopora" / "service_workflow_execution.py").read_text(encoding="utf-8")
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")

    assert "select_next_workflow_step" in workflow_source
    assert "select_next_workflow_step" in agent_source


def test_services_ask_run_engine_to_freeze_workflow_step_instructions() -> None:
    workflow_source = (REPO_ROOT / "src" / "loopora" / "service_workflow_execution.py").read_text(encoding="utf-8")
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")

    assert "RunEngineClaimWorkflowStepRequest" in workflow_source
    assert "RunEngineClaimWorkflowStepRequest" in agent_source
    assert "workflow_step_instruction" not in workflow_source
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

    assert claim_runtime_step.index(".claim_workflow_step(") < claim_runtime_step.index('state["active_step"] = {')


def test_agent_native_uses_run_engine_workflow_cursor_before_state_step_index() -> None:
    agent_source = (REPO_ROOT / "src" / "loopora" / "service_agent_native.py").read_text(encoding="utf-8")

    assert ".workflow_step_index(" in agent_source
    assert "fallback_step_index=int(state.get(\"step_index\") or 0)" in agent_source


def test_workflow_execution_submits_step_before_recording_step_evidence() -> None:
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    iteration_source = (REPO_ROOT / "src" / "loopora" / "service_workflow_iteration_state.py").read_text(encoding="utf-8")

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
    workflow_source = (REPO_ROOT / "src" / "loopora" / "service_workflow_execution.py").read_text(encoding="utf-8")
    commit_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_commit.py").read_text(encoding="utf-8")
    artifacts_source = (REPO_ROOT / "src" / "loopora" / "service_runner_step_artifacts.py").read_text(encoding="utf-8")

    assert "_commit_runner_step_result" in agent_source
    assert "_commit_runner_step_result" in workflow_source
    assert "class ServiceRunnerStepCommitMixin" in commit_source
    assert "class ServiceRunnerStepArtifactsMixin" in artifacts_source
    assert "_write_runner_step_result_artifacts" in commit_source
    assert "_commit_workflow_step_result" not in agent_source
    assert "_commit_workflow_step_result" not in workflow_source
    assert "_write_workflow_step_result" not in commit_source
