from __future__ import annotations

from pathlib import Path

from loopora.db import LooporaRepository
from loopora.service import LooporaService
from loopora.service_app import (
    AgentNativeService,
    AlignmentService,
    AssetRegistryService,
    BundleService,
    ProjectionService,
    RunService,
)
from loopora.settings import AppSettings


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
