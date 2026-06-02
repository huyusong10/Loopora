from __future__ import annotations

from pathlib import Path

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
from service_architecture_test_support import loopora_source


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
    service_app_source = loopora_source("service_app.py")
    service_alignment_source = loopora_source("service_alignment.py")
    alignment_status_source = loopora_source("service_alignment_status.py")
    web_alignment_event_api_source = loopora_source("web_alignment_event_api.py")

    assert "ServiceAlignmentMixin" not in source
    assert "ServiceLegacyExecutionMixin" not in source
    assert "ServiceWorkflowExecutionMixin" not in source
    assert "ServiceRunnerExecutionMixin" not in source
    assert "ServiceLegacyExecutionMixin" not in service_app_source
    assert "ServiceWorkflowExecutionMixin" not in service_app_source
    assert "service_legacy_execution" not in service_app_source
    assert "ServiceAlignmentLegacyMixin" not in service_alignment_source
    assert "ensure_alignment_session_layout" in loopora_source("service_alignment_session_layout_context.py")
    assert "ALIGNMENT_ACTIVE_STATUSES =" not in service_alignment_source
    assert "ALIGNMENT_ACTIVE_STATUSES =" in alignment_status_source
    assert "from loopora.service_alignment_status import ALIGNMENT_ACTIVE_STATUSES" in web_alignment_event_api_source
