from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loopora.diagnostics import log_event
from loopora.evidence_coverage_targets import with_coverage_targets
from loopora.run_artifacts import write_json_with_mirrors
from loopora.service_asset_common import logger, normalize_role_models
from loopora.service_run_start import ServiceRunStartMixin
from loopora.service_types import LooporaError
from loopora.strategy_source import strategy_source_has_finish_gatekeeper_step
from loopora.utils import make_id, write_json

import math

from dataclasses import replace



from loopora.executor_command_args import normalize_reasoning_effort, validate_command_args_text

from loopora.numeric_inputs import coerce_integral_number

from loopora.providers import executor_profile, normalize_executor_kind, normalize_executor_mode

from loopora.service_types import normalize_completion_mode

@dataclass(frozen=True, kw_only=True)
class LoopCreateRequest:
    name: str
    spec_path: Path
    workdir: Path
    model: str
    reasoning_effort: str
    max_iters: int
    max_role_retries: int
    delta_threshold: float
    trigger_window: int
    regression_window: int
    executor_kind: str = "codex"
    executor_mode: str = "preset"
    command_cli: str = ""
    command_args_text: str = ""
    workflow: dict | None = None
    prompt_files: dict | None = None
    orchestration_id: str | None = None
    role_models: dict | None = None
    completion_mode: str = "gatekeeper"
    iteration_interval_seconds: float = 0.0

def coerce_loop_create_request(
    request: LoopCreateRequest | None,
    raw_request: dict[str, Any],
) -> LoopCreateRequest:
    if request is not None and raw_request:
        raise TypeError("loop create request cannot mix object and keyword fields")
    return request or LoopCreateRequest(**raw_request)

def normalize_loop_create_request(request: LoopCreateRequest) -> LoopCreateRequest:
    workdir, spec_path = _normalize_loop_paths(request.workdir, request.spec_path)
    runtime_limits = _normalize_loop_limits(request)
    return replace(
        request,
        workdir=workdir,
        spec_path=spec_path,
        **runtime_limits,
        **_normalize_loop_executor_settings(request),
    )

def _normalize_loop_paths(workdir: Path, spec_path: Path) -> tuple[Path, Path]:
    normalized_workdir = workdir.expanduser().resolve()
    normalized_spec_path = spec_path.expanduser()
    if normalized_spec_path.exists():
        normalized_spec_path = normalized_spec_path.resolve()
    if not normalized_workdir.exists() or not normalized_workdir.is_dir():
        raise LooporaError(f"workdir does not exist: {normalized_workdir}")
    if not normalized_spec_path.exists():
        raise LooporaError(f"spec does not exist: {normalized_spec_path}")
    return normalized_workdir, normalized_spec_path

def _normalize_loop_limits(request: LoopCreateRequest) -> dict[str, int | float]:
    for field_name in (
        "iteration_interval_seconds",
        "max_iters",
        "max_role_retries",
        "delta_threshold",
        "trigger_window",
        "regression_window",
    ):
        _validate_finite_loop_number(getattr(request, field_name), field_name=field_name)
    try:
        max_iters = coerce_integral_number(request.max_iters, field_name="max_iters")
        max_role_retries = coerce_integral_number(request.max_role_retries, field_name="max_role_retries")
        trigger_window = coerce_integral_number(request.trigger_window, field_name="trigger_window")
        regression_window = coerce_integral_number(request.regression_window, field_name="regression_window")
    except ValueError as exc:
        raise LooporaError(str(exc)) from exc
    iteration_interval_seconds = float(request.iteration_interval_seconds)
    delta_threshold = float(request.delta_threshold)
    if max_iters < 0:
        raise LooporaError("max_iters must be >= 0")
    if max_role_retries < 0:
        raise LooporaError("max_role_retries must be >= 0")
    if iteration_interval_seconds < 0:
        raise LooporaError("iteration_interval_seconds must be >= 0")
    if delta_threshold < 0:
        raise LooporaError("delta_threshold must be >= 0")
    if trigger_window < 1:
        raise LooporaError("trigger_window must be >= 1")
    if regression_window < 1:
        raise LooporaError("regression_window must be >= 1")
    return {
        "iteration_interval_seconds": iteration_interval_seconds,
        "max_iters": max_iters,
        "max_role_retries": max_role_retries,
        "delta_threshold": delta_threshold,
        "trigger_window": trigger_window,
        "regression_window": regression_window,
    }

def _validate_finite_loop_number(value: object, *, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise LooporaError(f"{field_name} must be a finite number")

def _normalize_loop_executor_settings(request: LoopCreateRequest) -> dict[str, str]:
    try:
        executor_kind = normalize_executor_kind(request.executor_kind)
        executor_mode = normalize_executor_mode(request.executor_mode)
        profile = executor_profile(executor_kind)
        if profile.command_only and executor_mode != "command":
            raise ValueError(f"{profile.label} only supports command mode")
        model = request.model.strip()
        if executor_mode == "preset":
            return {
                "executor_kind": executor_kind,
                "executor_mode": executor_mode,
                "command_cli": "",
                "command_args_text": "",
                "model": model or profile.default_model,
                "reasoning_effort": normalize_reasoning_effort(request.reasoning_effort, executor_kind),
                "completion_mode": normalize_completion_mode(request.completion_mode),
            }
        command_cli = request.command_cli.strip() or profile.cli_name
        validate_command_args_text(request.command_args_text, executor_kind=executor_kind)
        return {
            "executor_kind": executor_kind,
            "executor_mode": executor_mode,
            "command_cli": command_cli,
            "command_args_text": request.command_args_text,
            "model": model,
            "reasoning_effort": request.reasoning_effort.strip(),
            "completion_mode": normalize_completion_mode(request.completion_mode),
        }
    except ValueError as exc:
        raise LooporaError(str(exc)) from exc


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
        self._persist_loop_definition_files(
            LoopDefinitionFiles(
                workdir=normalized_request.workdir,
                loop_id=loop_id,
                spec_markdown=spec_markdown,
                compiled_spec=compiled_spec,
                prompt_files=resolved_orchestration["prompt_files"],
                strategy_source=strategy_source,
            )
        )

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
            orchestration_id=request.orchestration_id,
            workflow=request.workflow,
            prompt_files=request.prompt_files,
            role_models=request.role_models,
        )

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
    def _read_and_compile_spec(spec_path: Path) -> tuple[str, dict]:
        from loopora.specs import read_and_compile

        return read_and_compile(spec_path)
