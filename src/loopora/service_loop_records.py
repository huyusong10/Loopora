from __future__ import annotations

from pathlib import Path

from loopora.branding import state_dir_for_workdir
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_asset_common import normalize_role_models
from loopora.service_types import LooporaNotFoundError
from loopora.strategy_source import (
    DEFAULT_STRATEGY_SOURCE_PRESET,
    StrategySourceError,
    build_preset_strategy_source,
    load_strategy_prompt_file,
    normalize_strategy_source,
    resolve_strategy_prompt_files,
    strategy_prompt_asset_path,
    strategy_source_from_record,
    strategy_source_warnings,
)
from loopora.task_verdicts import hydrate_run_status_and_task_verdict


class ServiceLoopRecordMixin:
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
