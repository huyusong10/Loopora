from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from typing import Any

from loopora.asset_catalog import AssetCatalogError, AssetCatalogNotFoundError, WorkflowAssetCatalog
from loopora.db import LooporaRepository
from loopora.executor import CodexExecutor, executor_from_environment
from loopora.service_agent_adapters import ServiceAgentAdapterMixin
from loopora.service_agent_native import ServiceAgentNativeMixin
from loopora.service_alignment import ServiceAlignmentMixin
from loopora.service_assets import ServiceAssetMixin
from loopora.service_iteration_reporting import ServiceIterationReportingMixin
from loopora.service_prompts import ServiceRunPromptMixin
from loopora.service_role_execution import ServiceRoleExecutionMixin
from loopora.service_role_requests import ServiceRoleRequestMixin
from loopora.service_run_finalization import ServiceRunFinalizationMixin
from loopora.service_run_lifecycle import ServiceRunLifecycleMixin
from loopora.service_types import LooporaError, LooporaNotFoundError
from loopora.service_workflow_execution import ServiceWorkflowExecutionMixin
from loopora.service_workflow_runtime import ServiceWorkflowRuntimeMixin
from loopora.service_workflow_support import ServiceWorkflowSupportMixin
from loopora.service_workspace import ServiceWorkspaceMixin
from loopora.settings import AppSettings
from loopora.workflows import WorkflowError


class _LooporaServiceRuntime(
    ServiceAgentAdapterMixin,
    ServiceAgentNativeMixin,
    ServiceAssetMixin,
    ServiceAlignmentMixin,
    ServiceRunPromptMixin,
    ServiceWorkflowSupportMixin,
    ServiceWorkflowRuntimeMixin,
    ServiceWorkflowExecutionMixin,
    ServiceRunFinalizationMixin,
    ServiceRoleRequestMixin,
    ServiceIterationReportingMixin,
    ServiceRoleExecutionMixin,
    ServiceRunLifecycleMixin,
    ServiceWorkspaceMixin,
):
    _process_active_runs: ClassVar[set[str]] = set()
    _process_active_runs_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        repository: LooporaRepository,
        settings: AppSettings,
        executor_factory: Callable[[], CodexExecutor] | None = None,
    ) -> None:
        self.repository = repository
        self.asset_catalog = WorkflowAssetCatalog(repository)
        self.settings = settings
        self.executor_factory = executor_factory or executor_from_environment
        self._threads: dict[str, threading.Thread] = {}
        self._reconcile_stale_runs()
        self._backfill_missing_run_takeaway_projections()

    def _loop_log_context(self, loop: dict | None, **context) -> dict[str, object]:
        payload = dict(context)
        if loop:
            payload.setdefault("loop_id", loop.get("id"))
            payload.setdefault("workdir", loop.get("workdir"))
            payload.setdefault("orchestration_id", loop.get("orchestration_id"))
        return payload

    def _run_log_context(self, run: dict | None, **context) -> dict[str, object]:
        payload = dict(context)
        if run:
            payload.setdefault("run_id", run.get("id"))
            payload.setdefault("loop_id", run.get("loop_id"))
            payload.setdefault("workdir", run.get("workdir"))
            payload.setdefault("orchestration_id", run.get("orchestration_id"))
        return payload

    def _asset_call(self, callback: Callable, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except AssetCatalogNotFoundError as exc:
            raise LooporaNotFoundError(str(exc)) from exc
        except AssetCatalogError as exc:
            raise LooporaError(str(exc)) from exc
        except (WorkflowError, ValueError) as exc:
            raise LooporaError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class _RuntimeComponent:
    runtime: _LooporaServiceRuntime


class AlignmentService(_RuntimeComponent):
    def get_workdir_context(self, workdir: Path) -> dict:
        return self.runtime.get_alignment_workdir_context(workdir)

    def resolve_context(
        self,
        workdir: Path,
        *,
        intent: str = "plan",
        adapter: str = "",
        context_id: str = "",
        source_option_id: str = "",
    ) -> dict:
        return self.runtime.resolve_loopora_context(
            workdir,
            intent=intent,
            adapter=adapter,
            context_id=context_id,
            source_option_id=source_option_id,
        )

    def list_sessions(self, *, limit: int = 30) -> list[dict]:
        return self.runtime.list_alignment_sessions(limit=limit)


class BundleService(_RuntimeComponent):
    def list_exchange_items(self) -> list[dict]:
        return self.runtime.list_bundle_exchange_items()

    def import_text(self, bundle_yaml: str, *, replace_bundle_id: str | None = None) -> dict:
        return self.runtime.import_bundle_text(bundle_yaml, replace_bundle_id=replace_bundle_id)

    def preview_text(self, bundle_yaml: str) -> dict:
        return self.runtime.preview_bundle_text(bundle_yaml)


class RunService(_RuntimeComponent):
    def get_run(self, run_id: str) -> dict:
        return self.runtime.get_run(run_id)

    def start_run(self, loop_id: str) -> dict:
        return self.runtime.start_run(loop_id)

    def start_run_async(self, run_id: str) -> None:
        self.runtime.start_run_async(run_id)

    def stop_run(self, run_id: str) -> dict:
        return self.runtime.stop_run(run_id)

    def stream_events(self, run_id: str, *, after_id: int = 0, limit: int = 200) -> list[dict]:
        return self.runtime.stream_events(run_id, after_id=after_id, limit=limit)

    def observation_snapshot(self, run_id: str) -> dict:
        return self.runtime.run_observation_snapshot(run_id)

    def runtime_activity(self) -> dict:
        return self.runtime.get_runtime_activity()


class AgentNativeService(_RuntimeComponent):
    def start_loop(self, adapter: str, **kwargs: Any) -> dict:
        return self.runtime.start_agent_loop(adapter, **kwargs)

    def prepare_run(self, adapter: str, run_id: str, *, entry_source: str = "") -> dict:
        return self.runtime.prepare_agent_native_run(adapter, run_id, entry_source=entry_source)

    def claim_step(self, request) -> dict[str, Any]:
        return self.runtime.claim_agent_native_step(request)

    def submit_step(self, request) -> dict[str, Any]:
        return self.runtime.submit_agent_native_step(request)

    def entry_loop_start_projection(self, loop_id: str) -> dict[str, Any]:
        return self.runtime.agent_entry_loop_start_projection(loop_id)


class AssetRegistryService(_RuntimeComponent):
    def local_diagnostics(self) -> dict:
        return self.runtime.local_asset_diagnostics()


class ProjectionService(_RuntimeComponent):
    def web_run_detail(self, run: dict[str, Any]) -> dict[str, Any]:
        from loopora.web_projection import web_run_detail_projection

        return web_run_detail_projection(run)


@dataclass(frozen=True, slots=True)
class LooporaAppServices:
    runtime: _LooporaServiceRuntime
    alignment: AlignmentService
    bundle: BundleService
    run: RunService
    agent_native: AgentNativeService
    asset_registry: AssetRegistryService
    projection: ProjectionService

    @classmethod
    def create(
        cls,
        *,
        repository: LooporaRepository,
        settings: AppSettings,
        executor_factory: Callable[[], CodexExecutor] | None = None,
    ) -> LooporaAppServices:
        runtime = _LooporaServiceRuntime(
            repository=repository,
            settings=settings,
            executor_factory=executor_factory,
        )
        return cls(
            runtime=runtime,
            alignment=AlignmentService(runtime),
            bundle=BundleService(runtime),
            run=RunService(runtime),
            agent_native=AgentNativeService(runtime),
            asset_registry=AssetRegistryService(runtime),
            projection=ProjectionService(runtime),
        )
