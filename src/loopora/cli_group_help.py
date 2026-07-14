from __future__ import annotations

from typing import Any

import typer
from typer.core import TyperCommand

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands


def print_help_when_no_subcommand(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


def help_first_typer(**kwargs: Any) -> typer.Typer:
    options = {"invoke_without_command": True, "callback": print_help_when_no_subcommand, **kwargs}
    return typer.Typer(**options)


class LooporaHelpCommand(TyperCommand):
    def get_help(self, ctx):
        return rewrite_loopora_help_commands(super().get_help(ctx))
