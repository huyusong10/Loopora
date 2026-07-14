from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.branding import state_dir_for_workdir
from loopora.diagnostics import log_event
from loopora.evidence_coverage_targets import with_coverage_targets
from loopora.run_artifacts import write_json_with_mirrors
from loopora.service_cleanup_diagnostics import best_effort_rmtree
from loopora.service_asset_common import logger, normalize_role_models
from loopora.service_loop_create_inputs import LoopCreateRequest, coerce_loop_create_request, normalize_loop_create_request
from loopora.service_run_start import ServiceRunStartMixin
from loopora.service_types import LooporaError
from loopora.strategy_source import strategy_source_has_finish_gatekeeper_step
from loopora.utils import make_id, write_json

LOOP_ARTIFACT_PREPARE_ERROR = "loop artifacts could not be prepared"


@dataclass(frozen=True, kw_only=True)
class LoopDefinitionFiles:
    workdir: Path
    loop_id: str
    spec_markdown: str
    compiled_spec: dict
    prompt_files: dict
    strategy_source: dict


@dataclass(frozen=True, kw_only=True)
class ResolvedLoopCreate:
    request: LoopCreateRequest
    loop_id: str
    spec_markdown: str
    compiled_spec: dict
    resolved_orchestration: dict
    strategy_source: dict


def _loop_create_payload(resolved: ResolvedLoopCreate) -> dict:
    request = resolved.request
    return {
        "id": resolved.loop_id,
        "name": request.name,
        "workdir": str(request.workdir),
        "spec_path": str(request.spec_path.resolve()),
        "spec_markdown": resolved.spec_markdown,
        "compiled_spec": resolved.compiled_spec,
        "executor_kind": request.executor_kind,
        "executor_mode": request.executor_mode,
        "command_cli": request.command_cli,
        "command_args_text": request.command_args_text,
        "model": request.model,
        "reasoning_effort": request.reasoning_effort,
        "completion_mode": request.completion_mode,
        "iteration_interval_seconds": request.iteration_interval_seconds,
        "max_iters": request.max_iters,
        "max_role_retries": request.max_role_retries,
        "delta_threshold": request.delta_threshold,
        "trigger_window": request.trigger_window,
        "regression_window": request.regression_window,
        "orchestration_id": resolved.resolved_orchestration["id"],
        "orchestration_name": resolved.resolved_orchestration["name"],
        "role_models": normalize_role_models(request.role_models),
        "workflow": resolved.strategy_source,
    }


class ServiceRunRegistrationMixin(ServiceRunStartMixin):
    def create_loop(
        self,
        request: LoopCreateRequest | None = None,
        **raw_request: Any,
    ) -> dict:
        loop_request = coerce_loop_create_request(request, raw_request)
        self._log_loop_create_requested(loop_request)
        normalized_request = normalize_loop_create_request(loop_request)
        resolved_orchestration = self._resolve_loop_orchestration(normalized_request)
        strategy_source = resolved_orchestration["workflow"]
        self._validate_loop_completion_strategy_source(
            completion_mode=normalized_request.completion_mode,
            strategy_source=strategy_source,
        )
        spec_markdown, compiled_spec = self._read_loop_spec_with_coverage(
            normalized_request.spec_path,
            completion_mode=normalized_request.completion_mode,
        )
        loop_id = make_id("loop")
        loop_definition_files = LoopDefinitionFiles(
            workdir=normalized_request.workdir,
            loop_id=loop_id,
            spec_markdown=spec_markdown,
            compiled_spec=compiled_spec,
            prompt_files=resolved_orchestration["prompt_files"],
            strategy_source=strategy_source,
        )
        try:
            self._persist_loop_definition_files(loop_definition_files)
        except OSError as exc:
            self._cleanup_failed_loop_definition_files(loop_definition_files)
            raise LooporaError(LOOP_ARTIFACT_PREPARE_ERROR) from exc
        except Exception:
            self._cleanup_failed_loop_definition_files(loop_definition_files)
            raise

        try:
            loop = self.repository.create_loop(
                _loop_create_payload(
                    ResolvedLoopCreate(
                        request=normalized_request,
                        loop_id=loop_id,
                        spec_markdown=spec_markdown,
                        compiled_spec=compiled_spec,
                        resolved_orchestration=resolved_orchestration,
                        strategy_source=strategy_source,
                    )
                )
            )
        except Exception:
            self._cleanup_failed_loop_definition_files(loop_definition_files)
            raise
        self._write_recent_workdirs()
        log_event(
            logger,
            logging.INFO,
            "service.loop.created",
            "Created loop definition",
            **self._loop_log_context(
                loop,
                spec_path=loop["spec_path"],
                loop_name=loop["name"],
                completion_mode=loop["completion_mode"],
            ),
        )
        return self._hydrate_loop_files(loop)

    def _log_loop_create_requested(self, request: LoopCreateRequest) -> None:
        log_event(
            logger,
            logging.INFO,
            "service.loop.create.requested",
            "Received loop creation request",
            workdir=request.workdir,
            spec_path=request.spec_path,
            orchestration_id=request.orchestration_id,
            completion_mode=request.completion_mode,
            max_iters=request.max_iters,
            executor_kind=request.executor_kind,
            executor_mode=request.executor_mode,
        )

    def _resolve_loop_orchestration(self, request: LoopCreateRequest) -> dict:
        return self._asset_call(
            self.asset_catalog.resolve_orchestration_input,
            orchestration_id=self._orchestration_id_for_loop_source(request),
            workflow=request.workflow,
            prompt_files=request.prompt_files,
            role_models=request.role_models,
        )

    @staticmethod
    def _orchestration_id_for_loop_source(request: LoopCreateRequest) -> str | None:
        if request.workflow is not None:
            return None
        return request.orchestration_id

    @staticmethod
    def _validate_loop_completion_strategy_source(*, completion_mode: str, strategy_source: dict) -> None:
        if completion_mode == "gatekeeper" and not strategy_source_has_finish_gatekeeper_step(strategy_source):
            raise LooporaError("gatekeeper completion mode requires a GateKeeper step that can finish the run")

    def _read_loop_spec_with_coverage(self, spec_path: Path, *, completion_mode: str) -> tuple[str, dict]:
        spec_markdown, compiled_spec = self._read_and_compile_spec(spec_path)
        return spec_markdown, with_coverage_targets(compiled_spec, completion_mode=completion_mode)

    def _persist_loop_definition_files(self, snapshot: LoopDefinitionFiles) -> None:
        loop_dir = self._ensure_loop_dir(snapshot.workdir, snapshot.loop_id)
        (loop_dir / "spec.md").write_text(snapshot.spec_markdown, encoding="utf-8")
        write_json(loop_dir / "compiled_spec.json", snapshot.compiled_spec)
        self._persist_prompt_files(loop_dir, snapshot.prompt_files)
        write_json_with_mirrors(loop_dir / "strategy_source.json", snapshot.strategy_source, mirror_paths=[loop_dir / "workflow.json"])

    @staticmethod
    def _cleanup_failed_loop_definition_files(snapshot: LoopDefinitionFiles) -> None:
        loop_dir = state_dir_for_workdir(snapshot.workdir) / "loops" / snapshot.loop_id
        best_effort_rmtree(
            loop_dir,
            logger,
            operation="loop_artifact_prepare_failed_cleanup",
            owner_id=snapshot.loop_id,
            workdir=str(snapshot.workdir),
        )

    @staticmethod
    def _read_and_compile_spec(spec_path: Path) -> tuple[str, dict]:
        from loopora.specs import read_and_compile

        return read_and_compile(spec_path)
