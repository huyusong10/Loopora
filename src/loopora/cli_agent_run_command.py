from __future__ import annotations

from pathlib import Path

import typer

from loopora.cli_agent_command_options import (
    AdapterRuntimeWorkdirOption,
    CompactJsonOutputOption,
    ContextIdOption,
    EntrySourceOption,
    NoWebOption,
    SourceOptionIdOption,
    effective_adapter_workdir,
)
from loopora.cli_agent_recovery import _print_agent_loop_unready_guidance
from loopora.cli_agent_runtime_actions import AgentLoopStartCliRequest, start_agent_loop_from_cli
from loopora.cli_agent_runtime_support import (
    attach_web_url,
    resolved_entry_source,
    spawn_agent_loop_worker_if_needed,
)
from loopora.cli_agent_step_presenters import _print_agent_loop_result
from loopora.cli_agent_workdir_recovery import (
    AgentRuntimeWorkdirRecoveryRequest,
    exit_if_unusable_agent_runtime_workdir,
)
from loopora.cli_shared import JsonOutputOption, get_service, handle_error
from loopora.service import LooporaError
from loopora.strategy_source import StrategySourceError


AGENT_RUN_HELP_EPILOG = (
    "This is the runtime command behind `/loopora-run`. Run it only after a READY preview has been reviewed in the "
    "same Agent context; it starts, resumes, or continues that reviewed Loop instead of creating a fresh plan or "
    "skipping review."
)


def register_agent_run_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    @adapter_app.command("run", epilog=AGENT_RUN_HELP_EPILOG)
    def agent_run(  # noqa: PLR0913 - managed run runtime exposes the stable Agent entry option surface.
        ctx: typer.Context,
        workdir: AdapterRuntimeWorkdirOption = Path(),
        context_id: ContextIdOption = "",
        source_option_id: SourceOptionIdOption = "",
        entry_source: EntrySourceOption = "",
        *,
        json_output: JsonOutputOption = False,
        compact_json_output: CompactJsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Start or reuse the Loopora run associated with the current ready Loop preview."""
        workdir = effective_adapter_workdir(ctx, workdir)
        service = None
        resolved_source = resolved_entry_source(entry_source)
        exit_if_unusable_agent_runtime_workdir(
            AgentRuntimeWorkdirRecoveryRequest(
                adapter=adapter,
                workdir=workdir,
                action="run",
                entry_source=resolved_source,
                json_output=json_output,
                compact_json_output=compact_json_output,
            )
        )
        try:
            service = get_service()
            result = start_agent_loop_from_cli(
                service,
                AgentLoopStartCliRequest(
                    adapter=adapter,
                    workdir=workdir,
                    context_id=context_id,
                    source_option_id=source_option_id,
                    entry_source=resolved_source,
                ),
            )
            spawn_agent_loop_worker_if_needed(service, result)
            attach_web_url(result, path_key="run_path", url_key="run_url", no_web=no_web, workdir=workdir)
            _print_agent_loop_result(result, json_output=json_output, compact_json_output=compact_json_output)
        except (LooporaError, StrategySourceError) as exc:
            if _print_agent_loop_unready_guidance(
                exc,
                service=service,
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                entry_source=resolved_source,
                no_web=no_web,
                json_output=json_output or compact_json_output,
            ):
                raise typer.Exit(code=1) from None
            handle_error(exc, json_output=json_output or compact_json_output, recovery_workdir=workdir)
