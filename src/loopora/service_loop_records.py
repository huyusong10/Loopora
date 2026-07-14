from __future__ import annotations

from loopora.events.projection_cache import run_projection_bundle_for_run
from loopora.loop_run_progress import build_loop_run_progress
from loopora.run_projection_fields import projection_first_run_record_fields
from loopora.service_asset_common import normalize_role_models
from loopora.service_loop_prompt_files import ServiceLoopPromptFileMixin
from loopora.service_types import LooporaNotFoundError
from loopora.strategy_source import (
    DEFAULT_STRATEGY_SOURCE_PRESET,
    StrategySourceError,
    build_preset_strategy_source,
    normalize_strategy_source,
    strategy_source_from_record,
    strategy_source_warnings,
)
from loopora.task_verdicts import hydrate_run_status_and_task_verdict


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
        loop["run_progress"] = build_loop_run_progress(loop["runs"])
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
            payload["run_progress"] = build_loop_run_progress(payload["runs"])
        else:
            payload = self._hydrate_run_files(payload)
            payload["continuation"] = self.run_continuation_state(str(payload["id"]))
        return kind, payload
