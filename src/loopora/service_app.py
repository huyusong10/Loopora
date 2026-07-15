from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from typing import Any

from loopora.asset_catalog import AssetCatalogError, AssetCatalogNotFoundError, StrategyTemplateAssetCatalog
from loopora.db import LooporaRepository
from loopora.executor import executor_from_environment
from loopora.executor_types import CodexExecutor
from loopora.service_agent_adapters import ServiceAgentAdapterMixin
from loopora.service_agent_native import ServiceAgentNativeMixin
from loopora.service_alignment import ServiceAlignmentMixin
from loopora.service_iteration_reporting import ServiceIterationReportingMixin
from loopora.service_prompts import ServiceRunPromptMixin
from loopora.service_role_execution import ServiceRoleExecutionMixin
from loopora.service_role_requests import ServiceRoleRequestMixin
from loopora.service_run_finalization import ServiceRunFinalizationMixin
from loopora.service_run_lifecycle import ServiceRunLifecycleMixin
from loopora.service_types import LooporaError, LooporaNotFoundError
from loopora.service_runner_execution import ServiceRunnerExecutionMixin
from loopora.service_runner_step_runtime import ServiceRunnerStepRuntimeMixin
from loopora.service_workspace import ServiceWorkspaceMixin
from loopora.settings import AppSettings
from loopora.strategy_source import StrategySourceError


from loopora.service_bundle_assets import ServiceBundleAssetMixin

from loopora.service_orchestration_assets import ServiceOrchestrationAssetMixin


from loopora.service_run_registration import ServiceRunRegistrationMixin

from loopora.events.projection_cache import run_projection_bundle_for_run

from loopora.run_projection_fields import projection_first_run_record_fields

from loopora.service_asset_common import normalize_role_models


from loopora.strategy_source import (
    DEFAULT_STRATEGY_SOURCE_PRESET,
    build_preset_strategy_source,
    normalize_strategy_source,
    strategy_source_from_record,
    strategy_source_warnings,
)

from loopora.task_verdicts import hydrate_run_status_and_task_verdict


from loopora.branding import state_dir_for_workdir

from loopora.run_artifacts import RunArtifactLayout

from loopora.strategy_source import (
    load_strategy_prompt_file,
    resolve_strategy_prompt_files,
    strategy_prompt_asset_path,
)

import logging

from loopora.asset_catalog import RoleDefinitionPayloadInput

from loopora.diagnostics import log_event

from loopora.service_asset_common import logger, record_bundle_asset_update_rollback_failure

from loopora.service_types import LooporaConflictError

from loopora.context_iteration_summary import IterationSummaryContext, build_iteration_summary, derive_latest_state

from loopora.run_artifacts import append_jsonl_with_mirrors

from loopora.runner_summary_projection import (
    build_runner_iteration_entry,
    build_runner_summary,
    summary_line_for_step,
)

from loopora.service_prompts import BUILDER_SCHEMA, CUSTOM_SCHEMA, GATEKEEPER_SCHEMA, GUIDE_SCHEMA, INSPECTOR_SCHEMA

from loopora.utils import read_json, utc_now, write_json

from loopora.runner_summary_projection import (
    IterationContextPersistRequest,
    RunnerSummaryRequest,
    StepOutputNormalizationRequest,
    StepOutputsWriteRequest,
)

from loopora.strategy_source import LEGACY_STRATEGY_ROLE_BY_ARCHETYPE

from loopora.runner_gatekeeper_output_validation import coerce_gatekeeper_output

class ServiceRunnerGatekeeperOutputMixin:
    def _coerce_gatekeeper_output(
        self,
        output: dict,
        *,
        evidence_context: dict | None = None,
        current_evidence_id: str = "",
        compiled_spec: dict | None = None,
    ) -> dict:
        return coerce_gatekeeper_output(
            output,
            evidence_context=evidence_context,
            current_evidence_id=current_evidence_id,
            compiled_spec=compiled_spec,
        )

def _safe_read_json_object(path) -> dict:
    try:
        payload = read_json(path)
    except (OSError, UnicodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}

class ServiceRunnerSupportMixin(ServiceRunnerGatekeeperOutputMixin):
    def _output_schema_for_archetype(self, archetype: str) -> dict:
        if archetype == "builder":
            return BUILDER_SCHEMA
        if archetype == "inspector":
            return INSPECTOR_SCHEMA
        if archetype == "gatekeeper":
            return GATEKEEPER_SCHEMA
        if archetype == "custom":
            return CUSTOM_SCHEMA
        return GUIDE_SCHEMA

    def _normalize_step_output(
        self,
        request: StepOutputNormalizationRequest,
    ) -> dict:
        if request.archetype == "inspector":
            return self._enrich_tester_result(request.output)
        if request.archetype == "gatekeeper":
            gatekeeper_output = self._coerce_gatekeeper_output(
                request.output,
                evidence_context=request.evidence_context,
                current_evidence_id=request.current_evidence_id,
                compiled_spec=request.compiled_spec,
            )
            return self._enrich_verifier_result(gatekeeper_output, request.compiled_spec, request.inspector_output or {})
        return dict(request.output)

    def _write_step_outputs(
        self,
        request: StepOutputsWriteRequest,
    ) -> None:
        step_dir = request.layout.step_dir(request.iter_id, request.step_order, request.step["id"])
        step_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            request.layout.step_output_normalized_path(request.iter_id, request.step_order, request.step["id"]),
            request.output,
        )
        write_json(
            request.layout.step_metadata_path(request.iter_id, request.step_order, request.step["id"]),
            {
                "step_id": request.step["id"],
                "step_order": request.step_order,
                "role_id": request.role["id"],
                "role_name": request.role["name"],
                "runtime_role": request.runtime_role,
                "archetype": request.role["archetype"],
                "iter": request.iter_id,
                "inherit_session": bool(request.step.get("inherit_session")),
                "extra_cli_args": str(request.step.get("extra_cli_args") or ""),
                "parallel_group": str(request.step.get("parallel_group") or ""),
                "inputs": dict(request.step.get("inputs") or {}),
                "action_policy": dict(request.step.get("action_policy") or {}),
                "control_id": str(request.step.get("control_id") or ""),
                "control": dict(request.step.get("control") or {}) if isinstance(request.step.get("control"), dict) else {},
            },
        )
        write_json(
            request.layout.step_handoff_path(request.iter_id, request.step_order, request.step["id"]),
            request.handoff,
        )

        for alias_path in request.layout.legacy_role_output_paths(request.role["archetype"]):
            write_json(alias_path, request.output)

    def _persist_iteration_context(
        self,
        request: IterationContextPersistRequest,
    ) -> dict:
        iteration_summary = build_iteration_summary(
            IterationSummaryContext(
                layout=request.layout,
                iter_id=request.iter_id,
                step_results=request.step_results,
                stagnation=request.stagnation,
                previous_composite=request.previous_composite,
                timestamp=utc_now(),
            )
        )
        write_json(request.layout.iteration_summary_path(request.iter_id), iteration_summary)
        append_jsonl_with_mirrors(request.layout.timeline_iterations_path, iteration_summary)
        latest_state = derive_latest_state(_safe_read_json_object(request.layout.latest_state_path), iteration_summary)
        write_json(request.layout.latest_iteration_summary_path, iteration_summary)
        write_json(request.layout.latest_state_path, latest_state)
        self.append_run_event(
            request.run_id,
            "iteration_summary_written",
            {
                "iter": request.iter_id,
                "summary_path": request.layout.relative(request.layout.iteration_summary_path(request.iter_id)),
                "latest_state_path": request.layout.relative(request.layout.latest_state_path),
                "executed_step_count": len(request.step_results),
                "composite_score": iteration_summary["score"]["composite"],
                "passed": iteration_summary["score"]["passed"],
            },
        )
        return iteration_summary

    def _build_runner_iteration_entry(
        self,
        iter_id: int,
        step_results: list[dict],
        stagnation: dict,
        *,
        previous_composite: float | None,
    ) -> dict:
        return build_runner_iteration_entry(
            iter_id,
            step_results,
            stagnation,
            previous_composite=previous_composite,
        )

    def _build_runner_summary(
        self,
        request: RunnerSummaryRequest,
    ) -> str:
        return build_runner_summary(request)

    def _summary_line_for_step(self, archetype: str, output: dict) -> str:
        return summary_line_for_step(archetype, output)

    def _runtime_role_key(self, role: dict) -> str:
        if role.get("id") == role.get("archetype"):
            return LEGACY_STRATEGY_ROLE_BY_ARCHETYPE.get(role["archetype"], role["id"])
        return role["id"]

class ServiceRoleDefinitionAssetMixin:
    def list_role_definitions(self) -> list[dict]:
        return self._asset_call(self.asset_catalog.list_role_definitions)

    def get_role_definition(self, role_definition_id: str) -> dict:
        return self._asset_call(self.asset_catalog.get_role_definition, role_definition_id)

    def create_role_definition(
        self,
        request: RoleDefinitionPayloadInput | None = None,
        **raw_payload: object,
    ) -> dict:
        role_definition = self._asset_call(
            self.asset_catalog.create_role_definition,
            request,
            **raw_payload,
        )
        log_event(
            logger,
            logging.INFO,
            "service.role_definition.created",
            "Created role definition",
            role_definition_id=role_definition["id"],
            archetype=role_definition["archetype"],
            executor_kind=role_definition.get("executor_kind"),
            role_name=role_definition["name"],
        )
        return role_definition

    def update_role_definition(
        self,
        role_definition_id: str,
        request: RoleDefinitionPayloadInput | None = None,
        **raw_payload: object,
    ) -> dict:
        bundle = None
        previous_role_definition = None
        if hasattr(self, "_bundle_record_for_role_definition_id"):
            bundle = self._bundle_record_for_role_definition_id(role_definition_id)
            if bundle:
                previous_role_definition = self.get_role_definition(role_definition_id)
        role_definition = self._asset_call(
            self.asset_catalog.update_role_definition,
            role_definition_id,
            request,
            **raw_payload,
        )
        if bundle and hasattr(self, "_touch_bundle_for_role_definition"):
            try:
                self._touch_bundle_for_role_definition(role_definition_id)
            except LooporaError:
                if previous_role_definition:
                    self.repository.update_role_definition(
                        role_definition_id,
                        {
                            "name": previous_role_definition["name"],
                            "description": previous_role_definition.get("description", ""),
                            "archetype": previous_role_definition["archetype"],
                            "prompt_ref": previous_role_definition["prompt_ref"],
                            "prompt_markdown": previous_role_definition["prompt_markdown"],
                            "posture_notes": previous_role_definition.get("posture_notes", ""),
                            "executor_kind": previous_role_definition.get("executor_kind", "codex"),
                            "executor_mode": previous_role_definition.get("executor_mode", "preset"),
                            "command_cli": previous_role_definition.get("command_cli", ""),
                            "command_args_text": previous_role_definition.get("command_args_text", ""),
                            "model": previous_role_definition.get("model", ""),
                            "reasoning_effort": previous_role_definition.get("reasoning_effort", ""),
                        },
                    )
                    if hasattr(self, "_sync_bundle_loop_snapshot"):
                        try:
                            self._sync_bundle_loop_snapshot(bundle["id"])
                        except Exception as rollback_exc:  # noqa: BLE001 - rollback diagnostics must preserve the original update error.
                            record_bundle_asset_update_rollback_failure(self, bundle, rollback_exc)
                raise
        log_event(
            logger,
            logging.INFO,
            "service.role_definition.updated",
            "Updated role definition",
            role_definition_id=role_definition["id"],
            archetype=role_definition["archetype"],
            executor_kind=role_definition.get("executor_kind"),
            role_name=role_definition["name"],
        )
        return role_definition

    def delete_role_definition(self, role_definition_id: str, *, allow_bundle_owned: bool = False) -> dict:
        if not allow_bundle_owned and hasattr(self, "_bundle_record_for_role_definition_id"):
            bundle = self._bundle_record_for_role_definition_id(role_definition_id)
            if bundle:
                raise LooporaConflictError(
                    f"role definition {role_definition_id} is managed by bundle {bundle['id']}; delete the bundle instead"
                )
        result = self._asset_call(self.asset_catalog.delete_role_definition, role_definition_id)
        log_event(
            logger,
            logging.INFO,
            "service.role_definition.deleted",
            "Deleted role definition",
            role_definition_id=role_definition_id,
        )
        return result

class ServiceLoopPromptFileMixin:
    def _prompt_dir(self, base_dir: Path) -> Path:
        return base_dir / "prompts"

    def _run_artifact_layout(self, run_dir: Path) -> RunArtifactLayout:
        return RunArtifactLayout(run_dir)

    def _persist_prompt_files(self, base_dir: Path, prompt_files: dict[str, str]) -> None:
        prompt_dir = self._prompt_dir(base_dir)
        prompt_dir.mkdir(parents=True, exist_ok=True)
        for prompt_ref, markdown_text in sorted(prompt_files.items()):
            path = strategy_prompt_asset_path(prompt_dir, prompt_ref)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(markdown_text), encoding="utf-8")

    def _read_prompt_files(self, base_dir: Path, strategy_source: dict) -> dict[str, str]:
        prompt_files: dict[str, str] = {}
        for role in strategy_source.get("roles", []):
            prompt_ref = str(role.get("prompt_ref", "")).strip()
            if not prompt_ref or prompt_ref in prompt_files:
                continue
            path = strategy_prompt_asset_path(self._prompt_dir(base_dir), prompt_ref)
            try:
                prompt_exists = path.exists()
                if prompt_exists:
                    prompt_files[prompt_ref] = load_strategy_prompt_file(path)
            except StrategySourceError as exc:
                if "could not be read" in str(exc):
                    raise StrategySourceError(f"prompt artifact {prompt_ref} could not be read") from exc
                raise StrategySourceError(f"prompt artifact {prompt_ref}: {exc}") from exc
            except OSError as exc:
                raise StrategySourceError(f"prompt artifact {prompt_ref} could not be read") from exc
        return resolve_strategy_prompt_files(strategy_source, prompt_files)

    def _read_prompt_files_for_loop(self, workdir: str, loop_id: str, strategy_source: dict) -> dict[str, str]:
        loop_dir = state_dir_for_workdir(workdir) / "loops" / loop_id
        return self._read_prompt_files(loop_dir, strategy_source)

    def _read_prompt_files_for_run(self, run: dict) -> dict[str, str]:
        strategy_source = self._normalized_strategy_source_from_record(run)
        layout = self._run_artifact_layout(Path(run["runs_dir"]))
        return self._read_prompt_files(layout.contract_dir, strategy_source)

class ServiceLoopRecordMixin(ServiceLoopPromptFileMixin):
    def _legacy_strategy_source_from_loop(self, loop_or_run: dict) -> dict:
        role_models = normalize_role_models(
            loop_or_run.get("role_models_json") or loop_or_run.get("role_models") or {}
        )
        return build_preset_strategy_source(DEFAULT_STRATEGY_SOURCE_PRESET, role_models=role_models)

    def _normalized_strategy_source_from_record(self, loop_or_run: dict) -> dict:
        return (
            self._strategy_source_snapshot_from_record(loop_or_run)
            or self._legacy_strategy_source_from_loop(loop_or_run)
        )

    def _strategy_source_snapshot_from_record(self, loop_or_run: dict) -> dict:
        strategy_source = strategy_source_from_record(loop_or_run)
        if strategy_source is None:
            return {}
        try:
            return normalize_strategy_source(strategy_source)
        except StrategySourceError:
            return strategy_source

    def _hydrate_loop_files(self, loop: dict) -> dict:
        if not loop:
            return loop
        strategy_source = self._normalized_strategy_source_from_record(loop)
        loop["strategy_source"] = strategy_source
        loop["workflow_json"] = strategy_source
        loop["workflow_warnings"] = strategy_source_warnings(strategy_source)
        if loop.get("orchestration_id"):
            loop["orchestration"] = {
                "id": loop.get("orchestration_id"),
                "name": loop.get("orchestration_name") or loop.get("orchestration_id"),
            }
        if hasattr(self, "_bundle_record_for_loop_id"):
            bundle = self._bundle_record_for_loop_id(loop["id"])
            if bundle:
                loop["bundle"] = {
                    "id": bundle["id"],
                    "name": bundle.get("name") or bundle["id"],
                }
        try:
            loop["prompt_files"] = self._read_prompt_files_for_loop(loop["workdir"], loop["id"], strategy_source)
        except StrategySourceError:
            loop["prompt_files"] = {}
        return loop

    def _hydrate_run_files(self, run: dict) -> dict:
        if not run:
            return run
        self._reap_terminal_thread_handle(run.get("id"), status=run.get("status"))
        hydrate_run_status_and_task_verdict(run)
        run_id = str(run.get("id") or "").strip()
        if run_id:
            projections = run_projection_bundle_for_run(self.repository, run_id)
            run.update(projection_first_run_record_fields(projections, run=run))
        strategy_source = self._normalized_strategy_source_from_record(run)
        run["strategy_source"] = strategy_source
        run["workflow_json"] = strategy_source
        run["workflow_warnings"] = strategy_source_warnings(strategy_source)
        if run.get("orchestration_id"):
            run["orchestration"] = {
                "id": run.get("orchestration_id"),
                "name": run.get("orchestration_name") or run.get("orchestration_id"),
            }
        try:
            run["prompt_files"] = self._read_prompt_files_for_run(run)
        except StrategySourceError:
            run["prompt_files"] = {}
        return run

    def list_loops(self) -> list[dict]:
        self._reconcile_local_orphaned_runs()
        return [self._hydrate_loop_files(loop) for loop in self.repository.list_loops()]

    def get_loop(self, loop_id: str) -> dict:
        self._reconcile_local_orphaned_runs()
        loop = self.repository.get_loop(loop_id)
        if not loop:
            raise LooporaNotFoundError(f"unknown loop: {loop_id}")
        loop = self._hydrate_loop_files(loop)
        loop["runs"] = [self._hydrate_run_files(run) for run in self.repository.list_runs_for_loop(loop_id)]
        return loop

    def get_run(self, run_id: str) -> dict:
        self._reconcile_local_orphaned_runs()
        run = self.repository.get_run(run_id)
        if not run:
            raise LooporaNotFoundError(f"unknown run: {run_id}")
        loop = self.repository.get_loop(run["loop_id"])
        if loop:
            run["loop_name"] = loop["name"]
        return self._hydrate_run_files(run)

    def get_status(self, identifier: str) -> tuple[str, dict]:
        self._reconcile_local_orphaned_runs()
        found = self.repository.get_loop_or_run(identifier)
        if not found:
            raise LooporaNotFoundError(f"unknown identifier: {identifier}")
        kind, payload = found
        if kind == "loop":
            payload = self._hydrate_loop_files(payload)
            payload["runs"] = [self._hydrate_run_files(run) for run in self.repository.list_runs_for_loop(payload["id"])]
        else:
            payload = self._hydrate_run_files(payload)
        return kind, payload

class ServiceAssetMixin(
    ServiceBundleAssetMixin,
    ServiceRunRegistrationMixin,
    ServiceLoopRecordMixin,
    ServiceOrchestrationAssetMixin,
    ServiceRoleDefinitionAssetMixin,
):
    """Backward-compatible aggregate mixin for loop/orchestration asset operations."""


class LooporaServiceRuntime(
    ServiceAgentAdapterMixin,
    ServiceAgentNativeMixin,
    ServiceAssetMixin,
    ServiceAlignmentMixin,
    ServiceRunPromptMixin,
    ServiceRunnerSupportMixin,
    ServiceRunnerStepRuntimeMixin,
    ServiceRunnerExecutionMixin,
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
        self.asset_catalog = StrategyTemplateAssetCatalog(repository)
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
        except (StrategySourceError, ValueError) as exc:
            raise LooporaError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class _RuntimeComponent:
    runtime: LooporaServiceRuntime


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
        from loopora.events.projection_cache import run_projection_bundle_for_run
        from loopora.web_projection import web_run_detail_projection

        return web_run_detail_projection(
            run,
            event_projections=run_projection_bundle_for_run(self.runtime.repository, str(run.get("id") or "")),
        )


@dataclass(frozen=True, slots=True)
class LooporaAppServices:
    runtime: LooporaServiceRuntime
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
        runtime = LooporaServiceRuntime(
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
