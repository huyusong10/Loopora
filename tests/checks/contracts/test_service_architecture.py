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
    ("src/loopora/service_agent_native.py", "loopora.service_workflow_execution", "_WorkflowIterationState"),
    ("src/loopora/service_agent_native.py", "loopora.service_workflow_execution", "_WorkflowRunContext"),
    ("src/loopora/service_agent_native.py", "loopora.service_workflow_execution", "_evidence_context_with_canonical_items"),
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

    assert "ServiceAlignmentMixin" not in source
    assert "ServiceLegacyExecutionMixin" not in source
    assert "ServiceWorkflowExecutionMixin" not in source


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
