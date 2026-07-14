from __future__ import annotations

from typer.core import TyperGroup

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_adapter_recovery import UnsupportedAgentAdapterCommand, _normalized_adapter_alias
from loopora.cli_slash_recovery import SlashCommandRecovery, _normalized_slash_recovery_command


def _help_with_current_loopora_entry(help_text: str) -> str:
    return rewrite_loopora_help_commands(help_text)


class LooporaRootHelpGroup(TyperGroup):
    def get_help(self, ctx):
        return _help_with_current_loopora_entry(super().get_help(ctx))

    def list_commands(self, ctx):
        names = super().list_commands(ctx)
        first_use_order = {
            "start": 0,
            "fit": 1,
            "demo": 2,
            "serve": 3,
            "init": 4,
            "doctor": 5,
            "support": 6,
            "version": 7,
            "uninstall": 8,
            "loops": 9,
            "bundles": 10,
            "diagnose": 11,
            "recovery": 12,
            "run": 13,
            "orchestrations": 14,
            "roles": 15,
            "spec": 16,
            "prompts": 17,
            "dev": 18,
            "agent": 19,
        }
        original_order = {name: index for index, name in enumerate(names)}
        return sorted(names, key=lambda name: (first_use_order.get(name, 100), original_order[name]))

    def get_command(self, ctx, cmd_name):
        command = super().get_command(ctx, cmd_name)
        if command is None:
            recovery_command = _normalized_slash_recovery_command(str(cmd_name or ""))
            if recovery_command:
                return SlashCommandRecovery(recovery_command)
        return command


class AgentAdapterCommandGroup(TyperGroup):
    loopora_adapter_group = "agent"

    def get_help(self, ctx):
        return _help_with_current_loopora_entry(super().get_help(ctx))

    def get_command(self, ctx, cmd_name):
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        adapter = str(cmd_name or "").strip()
        normalized = _normalized_adapter_alias(adapter)
        if normalized and normalized != adapter:
            alias_command = super().get_command(ctx, normalized)
            if alias_command is not None:
                return alias_command
        if adapter:
            return UnsupportedAgentAdapterCommand(adapter, command_group=self.loopora_adapter_group)
        return None


class InitAdapterCommandGroup(AgentAdapterCommandGroup):
    loopora_adapter_group = "init"


class UninstallAdapterCommandGroup(AgentAdapterCommandGroup):
    loopora_adapter_group = "uninstall"


class AgentRuntimeAdapterCommandGroup(AgentAdapterCommandGroup):
    loopora_adapter_group = "agent"
