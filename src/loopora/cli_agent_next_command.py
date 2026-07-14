from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer

from loopora.cli_agent_command_options import (
    AdapterRuntimeWorkdirOption,
    CompactJsonOutputOption,
    ContextIdOption,
    EntrySourceOption,
    NextStepIdCompatOption,
    NoWebOption,
    RunIdOption,
    effective_adapter_workdir,
)
from loopora.cli_agent_runtime_actions import AgentNextCliRequest
from loopora.cli_agent_runtime_support import resolved_entry_source
from loopora.cli_agent_workdir_recovery import (
    AgentRuntimeWorkdirRecoveryRequest,
    exit_if_unusable_agent_runtime_workdir,
)
from loopora.cli_shared import JsonOutputOption


AGENT_NEXT_HELP_EPILOG = (
    "This is host-Agent runtime plumbing after `/loopora-run` has started a run. It claims the current step contract "
    "for native execution; use the returned context, step contract, and result template before submitting evidence."
)
AgentNextClaim = Callable[[AgentNextCliRequest], None]


def register_agent_next_command(
    adapter_app: typer.Typer,
    *,
    adapter: str,
    claim_from_cli: AgentNextClaim,
) -> None:
    @adapter_app.command("next", epilog=AGENT_NEXT_HELP_EPILOG)
    def agent_next(  # noqa: PLR0913 - native step claim exposes the stable Agent entry option surface.
        ctx: typer.Context,
        workdir: AdapterRuntimeWorkdirOption = Path(),
        context_id: ContextIdOption = "",
        run_id: RunIdOption = "",
        _step_id: NextStepIdCompatOption = "",
        entry_source: EntrySourceOption = "",
        *,
        json_output: JsonOutputOption = False,
        compact_json_output: CompactJsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Claim the next Loopora step contract for the host Agent to execute natively."""
        workdir = effective_adapter_workdir(ctx, workdir)
        resolved_source = resolved_entry_source(entry_source)
        exit_if_unusable_agent_runtime_workdir(
            AgentRuntimeWorkdirRecoveryRequest(
                adapter=adapter,
                workdir=workdir,
                action="next",
                entry_source=resolved_source,
                json_output=json_output,
                compact_json_output=compact_json_output,
            )
        )
        claim_from_cli(
            AgentNextCliRequest(
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                run_id=run_id,
                entry_source=resolved_source,
                json_output=json_output,
                compact_json_output=compact_json_output,
                no_web=no_web,
            ),
        )
