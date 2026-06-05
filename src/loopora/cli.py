from __future__ import annotations

import click
import typer
from typer.core import TyperGroup

from loopora.agent_adapters import adapter_first_task_message_example
from loopora.branding import APP_NAME
from loopora.cli_agent_adapter_commands import register_agent_adapter_commands
from loopora.cli_bundle_commands import register_bundle_commands
from loopora.cli_diagnose_commands import register_diagnose_commands
from loopora.cli_common import echo_json
from loopora.cli_dev_commands import register_dev_commands
from loopora.cli_runtime import set_service_factory, set_worker_spawner
from loopora.cli_shared import spawn_background_worker as _spawn_background_worker
from loopora.cli_loop_commands import register_loop_commands
from loopora.cli_orchestration_commands import register_orchestration_commands
from loopora.cli_prompt_commands import register_prompt_commands
from loopora.cli_role_commands import register_role_commands
from loopora.cli_root_commands import register_root_commands
from loopora.cli_spec_commands import register_spec_commands
from loopora.service import create_service


def _current_service_factory():
    return create_service()


def _current_worker_spawner(service, run):
    return _spawn_background_worker(service, run)


set_service_factory(_current_service_factory)
set_worker_spawner(_current_worker_spawner)


class LooporaRootHelpGroup(TyperGroup):
    def list_commands(self, ctx):
        names = super().list_commands(ctx)
        first_use_order = {
            "init": 0,
            "serve": 1,
            "uninstall": 2,
            "loops": 3,
            "bundles": 4,
            "diagnose": 5,
            "run": 6,
            "orchestrations": 7,
            "roles": 8,
            "spec": 9,
            "prompts": 10,
            "dev": 11,
            "agent": 12,
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


class SlashCommandRecovery(click.Command):
    def __init__(self, slash_command: str):
        super().__init__(
            slash_command,
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
        )
        self.slash_command = slash_command

    def get_help(self, _ctx):
        return _slash_command_recovery_message(self.slash_command)

    def invoke(self, ctx):
        if _slash_recovery_wants_json(ctx):
            echo_json(_slash_command_recovery_json_payload(self.slash_command))
        else:
            typer.echo(_slash_command_recovery_message(self.slash_command))
        raise typer.Exit(code=2)


def _normalized_slash_recovery_command(command: str) -> str:
    normalized = str(command or "").strip()
    if normalized.startswith("/"):
        return normalized
    if normalized in {"loopora-plan", "loopora-run", "next"}:
        return f"/{normalized}"
    return ""


def _slash_recovery_wants_json(ctx) -> bool:
    return any(str(arg or "").strip() == "--json" for arg in list(getattr(ctx, "args", []) or []))


def _slash_command_recovery_json_payload(slash_command: str) -> dict:
    payload = _slash_command_recovery_payload(slash_command)
    return {"slash_command_recovery_summary": _slash_command_recovery_summary(payload), **payload}


def _slash_command_recovery_summary(payload: dict) -> dict:
    summary_keys = [
        "ready",
        "slash_command_recovery",
        "slash_command",
        "agent_command",
        "shell_subcommand",
        "next_step",
        "install_first",
        "if_missing_in_agent",
        "debug_cli",
    ]
    return {key: payload[key] for key in summary_keys if key in payload and payload[key] not in ("", [], {})}


def _slash_command_recovery_payload(slash_command: str) -> dict:
    command = str(slash_command or "").strip()
    if command == "/loopora-plan":
        return {
            "ready": False,
            "slash_command_recovery": "agent_slash_command_in_shell",
            "slash_command": "/loopora-plan",
            "agent_command": True,
            "shell_subcommand": False,
            "message": "/loopora-plan is an Agent slash command, not a shell subcommand.",
            "install_first": 'loopora init codex --workdir "$PWD"  # or claude/opencode',
            "if_missing_in_agent": 'loopora init codex --workdir "$PWD" --check  # then refresh or restart that Agent',
            "next_step": "return to that Agent with the task goal, fake-done risk, and required evidence, then run /loopora-plan there.",
            "first_task_message_example": adapter_first_task_message_example(),
            "debug_cli": 'loopora agent codex plan --workdir "$PWD" --message "<task goal and evidence expectations>"',
        }
    if command == "/loopora-run":
        return {
            "ready": False,
            "slash_command_recovery": "agent_slash_command_in_shell",
            "slash_command": "/loopora-run",
            "agent_command": True,
            "shell_subcommand": False,
            "message": "/loopora-run is an Agent slash command, not a shell subcommand.",
            "if_missing_in_agent": 'loopora init codex --workdir "$PWD" --check  # then refresh or restart that Agent',
            "next_step": "run /loopora-run inside the same Agent session that created or selected the READY Loop preview.",
            "debug_cli": 'loopora agent codex run --workdir "$PWD"  # use claude/opencode for that adapter',
        }
    if command == "/next":
        return {
            "ready": False,
            "slash_command_recovery": "unsupported_loopora_slash_command",
            "slash_command": "/next",
            "agent_command": False,
            "shell_subcommand": False,
            "message": "Loopora does not install a top-level /next slash command.",
            "next_step": "use /loopora-run inside the Agent to start, resume, or continue the current Loop.",
            "debug_cli": 'loopora agent codex next --workdir "$PWD" --run-id <run_id>',
        }
    return {
        "ready": False,
        "slash_command_recovery": "unknown_loopora_shell_subcommand",
        "slash_command": command,
        "agent_command": False,
        "shell_subcommand": False,
        "message": f"{command} is not a Loopora shell subcommand.",
        "known_agent_commands": ["/loopora-plan", "/loopora-run"],
        "install_first": 'loopora init codex --workdir "$PWD"  # or claude/opencode',
        "if_missing_in_agent": 'loopora init codex --workdir "$PWD" --check  # then refresh or restart that Agent',
        "first_task_message_example": adapter_first_task_message_example(),
        "next_step": "run Loopora slash commands inside the Coding Agent, not in the shell.",
    }


def _slash_command_recovery_message(slash_command: str) -> str:
    payload = _slash_command_recovery_payload(slash_command)
    lines = [f"slash_command_recovery: {payload['message']}"]
    known_agent_commands = payload.get("known_agent_commands")
    if isinstance(known_agent_commands, list) and known_agent_commands:
        lines.append("known_agent_commands: " + ", ".join(str(item) for item in known_agent_commands))
    for key in ("install_first", "if_missing_in_agent", "next_step", "first_task_message_example", "debug_cli"):
        value = str(payload.get(key) or "").strip()
        if value:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


app = typer.Typer(
    cls=LooporaRootHelpGroup,
    help=(
        f"{APP_NAME} CLI\n\n"
        "Start here: in the project where your Coding Agent will work, run "
        "`loopora init codex`, `loopora init claude`, or `loopora init opencode`, "
        "then return to that Agent with the task goal, fake-done risk, and required evidence. "
        "Run `/loopora-plan`, review the Loop preview, then run `/loopora-run` in the same Agent session."
    )
)
loops_app = typer.Typer(help="Inspect and run saved Loops")
orchestrations_app = typer.Typer(help="Expert: create and inspect reusable run flows")
roles_app = typer.Typer(help="Expert: create and inspect reusable role definitions")
bundles_app = typer.Typer(help="Import, export, and manage Loop plan files")
spec_app = typer.Typer(help="Expert: work with Markdown Loop contracts")
prompts_app = typer.Typer(help="Developer: validate and inspect prompt templates")
diagnose_app = typer.Typer(help="Inspect local diagnostics and repair safe historical issues")
dev_app = typer.Typer(help="Developer: reset incompatible development local state")
init_app = typer.Typer(
    help=(
        "Install /loopora-plan and /loopora-run project entries, then return to the Agent "
        "with the task goal, fake-done risk, and required evidence."
    )
)
uninstall_app = typer.Typer(help="Remove Loopora-managed Coding Agent project entries")
agent_app = typer.Typer(help="Internal runtime used by /loopora-plan and /loopora-run project entries")

app.add_typer(init_app, name="init")
app.add_typer(uninstall_app, name="uninstall")
app.add_typer(loops_app, name="loops")
app.add_typer(orchestrations_app, name="orchestrations")
app.add_typer(roles_app, name="roles")
app.add_typer(bundles_app, name="bundles")
app.add_typer(spec_app, name="spec")
app.add_typer(prompts_app, name="prompts")
app.add_typer(diagnose_app, name="diagnose")
app.add_typer(dev_app, name="dev")
app.add_typer(agent_app, name="agent")

register_root_commands(app)
register_loop_commands(loops_app)
register_orchestration_commands(orchestrations_app)
register_role_commands(roles_app)
register_bundle_commands(bundles_app)
register_spec_commands(spec_app)
register_prompt_commands(prompts_app)
register_diagnose_commands(diagnose_app)
register_dev_commands(dev_app)
register_agent_adapter_commands(init_app, uninstall_app, agent_app)

__all__ = ["_spawn_background_worker", "app", "create_service"]
