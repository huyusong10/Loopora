from __future__ import annotations

from pathlib import Path

import typer

from loopora.cli_agent_command_options import (
    AdapterMessageOption,
    AdapterRuntimeWorkdirOption,
    BundleFileOption,
    CompactJsonOutputOption,
    ContextIdOption,
    EntrySourceOption,
    NoWebOption,
    effective_adapter_workdir,
)
from loopora.cli_agent_plan_output import _print_agent_gen_result
from loopora.cli_agent_runtime_actions import AgentPlanErrorCliRequest, handle_agent_plan_error
from loopora.cli_agent_runtime_support import attach_web_url, resolved_entry_source
from loopora.cli_agent_workdir_recovery import (
    AgentRuntimeWorkdirRecoveryRequest,
    exit_if_unusable_agent_runtime_workdir,
)
from loopora.cli_shared import JsonOutputOption, get_service
from loopora.service import LooporaError
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.strategy_source import StrategySourceError


AGENT_PLAN_HELP_EPILOG = (
    "This is the runtime command behind `/loopora-plan`, not a replacement for the managed Agent entry. "
    "Use it from shell only for entry diagnostics or non-interactive recovery: keep the full task judgment in "
    "`--message`, submit only explicitly confirmed candidate files, and review the READY preview before any run starts."
)


def register_agent_plan_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    @adapter_app.command("plan", epilog=AGENT_PLAN_HELP_EPILOG)
    def agent_plan(  # noqa: PLR0913 - managed plan runtime exposes the stable Agent entry option surface.
        ctx: typer.Context,
        workdir: AdapterRuntimeWorkdirOption = Path(),
        message: AdapterMessageOption = "",
        bundle_file: BundleFileOption = None,
        context_id: ContextIdOption = "",
        entry_source: EntrySourceOption = "",
        *,
        json_output: JsonOutputOption = False,
        compact_json_output: CompactJsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Validate a confirmed candidate plan or open non-interactive Web alignment."""
        workdir = effective_adapter_workdir(ctx, workdir)
        resolved_source = resolved_entry_source(entry_source)
        exit_if_unusable_agent_runtime_workdir(
            AgentRuntimeWorkdirRecoveryRequest(
                adapter=adapter,
                workdir=workdir,
                action="plan",
                entry_source=resolved_source,
                json_output=json_output,
                compact_json_output=compact_json_output,
            )
        )
        try:
            request = AgentBundleCandidateRequest(
                adapter=adapter,
                workdir=workdir,
                message=message,
                bundle_file=bundle_file,
                context_id=context_id,
                entry_source=resolved_source,
            )
            result = get_service().create_agent_bundle_candidate(request)
            attach_web_url(result, path_key="preview_path", url_key="preview_url", no_web=no_web, workdir=workdir)
            _print_agent_gen_result(result, json_output=json_output, compact_json_output=compact_json_output)
        except (LooporaError, StrategySourceError) as exc:
            handle_agent_plan_error(
                exc,
                AgentPlanErrorCliRequest(
                    adapter=adapter,
                    workdir=workdir,
                    context_id=context_id,
                    entry_source=resolved_source,
                    message=message,
                    bundle_file=bundle_file,
                    json_output=json_output or compact_json_output,
                ),
            )
