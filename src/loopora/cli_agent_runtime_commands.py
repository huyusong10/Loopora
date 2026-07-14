from __future__ import annotations

import typer

from loopora import cli_agent_adapter_lifecycle_commands as _agent_adapter_lifecycle_commands
from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_agent_command_options import AdapterGroupWorkdirOption
from loopora.cli_agent_group_previews import agent_runtime_adapter_preview
from loopora.cli_agent_next_command import AGENT_NEXT_HELP_EPILOG as AGENT_NEXT_HELP_EPILOG
from loopora.cli_agent_next_command import register_agent_next_command
from loopora.cli_agent_plan_command import AGENT_PLAN_HELP_EPILOG as AGENT_PLAN_HELP_EPILOG
from loopora.cli_agent_plan_command import register_agent_plan_command
from loopora.cli_agent_run_command import AGENT_RUN_HELP_EPILOG as AGENT_RUN_HELP_EPILOG
from loopora.cli_agent_run_command import register_agent_run_command
from loopora.cli_agent_runtime_actions import AgentNextCliRequest
from loopora.cli_agent_runtime_actions import claim_agent_next_from_cli as claim_agent_next_from_cli
from loopora.cli_agent_submit_command import AGENT_SUBMIT_HELP_EPILOG as AGENT_SUBMIT_HELP_EPILOG
from loopora.cli_agent_submit_command import register_agent_submit_command
from loopora.cli_group_help import help_first_typer


AGENT_RUNTIME_HELP_EPILOG = (
    "This adapter runtime is normally called by Loopora-managed Agent entries, not by first-use shell workflows. "
    "If you are choosing how to start, run `loopora start` first, then use `loopora fit` when fit is uncertain. "
    "Outside an Agent session, open Fit Guide/Web choices in Web with "
    '`loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742` for conversation, import, or manual paths. '
    'Same-Agent setup for this adapter uses `loopora init {adapter} --workdir "$PWD"`, then '
    '`loopora doctor --workdir "$PWD"`; after readiness passes, return to that Agent for `/loopora-plan` and '
    "`/loopora-run`. "
    'Use `loopora agent {adapter} check --workdir "$PWD"` only when you need a CLI diagnostic for the installed entry.'
)


def register_agent_runtime_commands(agent_app: typer.Typer) -> None:
    _register_agent_runtime_for(agent_app, adapter="codex", help_text="Internal Codex runtime used by Loopora project entries")
    _register_agent_runtime_for(agent_app, adapter="claude", help_text="Internal Claude Code runtime used by Loopora project entries")
    _register_agent_runtime_for(agent_app, adapter="opencode", help_text="Internal OpenCode runtime used by Loopora project entries")


def _register_agent_runtime_for(agent_app: typer.Typer, *, adapter: str, help_text: str) -> None:
    def adapter_callback(ctx: typer.Context, workdir: AdapterGroupWorkdirOption = None) -> None:
        if ctx.invoked_subcommand is not None:
            return
        if workdir is not None:
            typer.echo(agent_runtime_adapter_preview(adapter, workdir))
        else:
            typer.echo(ctx.get_help())
        raise typer.Exit

    adapter_app = help_first_typer(
        callback=adapter_callback,
        help=help_text,
        epilog=rewrite_loopora_help_commands(AGENT_RUNTIME_HELP_EPILOG.format(adapter=adapter)),
    )
    agent_app.add_typer(adapter_app, name=adapter)
    _agent_adapter_lifecycle_commands.register_agent_check_command(adapter_app, adapter=adapter)
    _register_agent_plan_command(adapter_app, adapter=adapter)
    _register_agent_run_command(adapter_app, adapter=adapter)
    _register_agent_next_command(adapter_app, adapter=adapter)
    _register_agent_submit_command(adapter_app, adapter=adapter)


def _register_agent_plan_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    register_agent_plan_command(adapter_app, adapter=adapter)


def _register_agent_run_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    register_agent_run_command(adapter_app, adapter=adapter)


def _register_agent_next_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    register_agent_next_command(adapter_app, adapter=adapter, claim_from_cli=_claim_agent_next_from_cli_compat)


def _register_agent_submit_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    register_agent_submit_command(adapter_app, adapter=adapter)


def _claim_agent_next_from_cli_compat(request: AgentNextCliRequest) -> None:
    claim_agent_next_from_cli(request)
