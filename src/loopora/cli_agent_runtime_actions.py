from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer

from loopora.cli_agent_recovery import (
    _print_agent_next_recovery_guidance as _print_agent_next_recovery_guidance,
    _print_agent_plan_recovery_guidance as _print_agent_plan_recovery_guidance,
)
from loopora.cli_agent_runtime_support import (
    attach_web_url as _attach_web_url,
    resolved_entry_source as _resolved_entry_source,
)
from loopora.cli_agent_step_presenters import _print_agent_next_result as _print_agent_next_result
from loopora.cli_agent_submit_repair import _print_agent_submit_repair_guidance as _print_agent_submit_repair_guidance
from loopora.cli_shared import get_service, handle_error
from loopora.service import LooporaError
from loopora.service_agent_native import AgentNativeStepClaimRequest
from loopora.strategy_source import StrategySourceError


@dataclass(frozen=True)
class AgentNextCliRequest:
    adapter: str
    workdir: Path
    context_id: str
    run_id: str
    entry_source: str
    json_output: bool
    no_web: bool
    compact_json_output: bool = False


@dataclass(frozen=True)
class AgentSubmitErrorCliRequest:
    service: object
    adapter: str
    context_id: str
    run_id: str
    entry_source: str
    result_file: Path
    workdir: Path
    json_output: bool
    auto_repair_actions: list[str] | None = None


@dataclass(frozen=True)
class AgentPlanErrorCliRequest:
    adapter: str
    workdir: Path
    context_id: str
    entry_source: str
    json_output: bool


@dataclass(frozen=True)
class AgentLoopStartCliRequest:
    adapter: str
    workdir: Path
    context_id: str
    source_option_id: str
    entry_source: str


def claim_agent_next_from_cli(request: AgentNextCliRequest) -> None:
    service = get_service()
    resolved_entry_source = _resolved_entry_source(request.entry_source)
    try:
        result = service.claim_agent_native_step(
            AgentNativeStepClaimRequest(
                adapter=request.adapter,
                workdir=request.workdir,
                context_id=request.context_id,
                run_id=request.run_id,
                entry_source=resolved_entry_source,
            )
        )
        _attach_web_url(result, path_key="run_path", url_key="run_url", no_web=request.no_web)
        _print_agent_next_result(result, json_output=request.json_output, compact_json_output=request.compact_json_output)
    except (LooporaError, StrategySourceError) as exc:
        if _print_agent_next_recovery_guidance(
            exc,
            service=service,
            adapter=request.adapter,
            workdir=request.workdir,
            context_id=request.context_id,
            entry_source=resolved_entry_source,
            no_web=request.no_web,
            json_output=request.json_output or request.compact_json_output,
        ):
            raise typer.Exit(code=1) from None
        handle_error(exc)


def handle_agent_submit_error(
    exc: LooporaError | StrategySourceError,
    request: AgentSubmitErrorCliRequest,
) -> None:
    if _print_agent_submit_repair_guidance(
        exc,
        service=request.service,
        adapter=request.adapter,
        context_id=request.context_id,
        run_id=request.run_id,
        entry_source=request.entry_source,
        result_file=request.result_file,
        workdir=request.workdir,
        json_output=request.json_output,
        auto_repair_actions=request.auto_repair_actions or [],
    ):
        raise typer.Exit(code=1)
    handle_error(exc)


def handle_agent_plan_error(
    exc: LooporaError | StrategySourceError,
    request: AgentPlanErrorCliRequest,
) -> None:
    if _print_agent_plan_recovery_guidance(
        exc,
        adapter=request.adapter,
        workdir=request.workdir,
        context_id=request.context_id,
        entry_source=request.entry_source,
        json_output=request.json_output,
    ):
        raise typer.Exit(code=1)
    handle_error(exc)


def start_agent_loop_from_cli(
    service,
    request: AgentLoopStartCliRequest,
) -> dict:
    start_kwargs = {
        "workdir": request.workdir,
        "context_id": request.context_id,
        "entry_source": request.entry_source,
        "execute_async": False,
    }
    if request.source_option_id:
        start_kwargs["source_option_id"] = request.source_option_id
    return service.start_agent_loop(request.adapter, **start_kwargs)
