from __future__ import annotations

import typer

from loopora import cli_agent_adapter_lifecycle_commands as _agent_adapter_lifecycle_commands
from loopora import cli_agent_runtime_support as _agent_runtime_support
from loopora import cli_agent_context_recovery_output as _agent_context_recovery_output
from loopora import cli_agent_recovery as _agent_recovery
from loopora import cli_agent_runtime_commands as _agent_runtime_commands
from loopora import cli_agent_plan_output as _agent_plan_output
from loopora import cli_agent_step_presenters as _agent_step_presenters
from loopora import cli_agent_adapter_output as _agent_adapter_output
from loopora import cli_agent_runtime_actions as _agent_runtime_actions
from loopora import cli_agent_submit_auto_repair as _agent_submit_auto_repair
from loopora import cli_agent_submit_repair as _agent_submit_repair
from loopora import cli_agent_current_step_output as _agent_current_step_output

_agent_plan_cli_command = _agent_runtime_support.agent_plan_cli_command
_agent_next_command_hint = _agent_runtime_support.agent_next_command_hint
_attach_recoverable_context_preview_urls = _agent_runtime_support.attach_recoverable_context_preview_urls
_check_adapter = _agent_adapter_lifecycle_commands._check_adapter
_install_adapter = _agent_adapter_lifecycle_commands._install_adapter
_uninstall_adapter = _agent_adapter_lifecycle_commands._uninstall_adapter

_PRIVATE_COMPAT_MODULES = (
    _agent_runtime_support,
    _agent_recovery,
    _agent_adapter_output,
    _agent_runtime_actions,
    _agent_runtime_commands,
    _agent_plan_output,
    _agent_context_recovery_output,
    _agent_current_step_output,
    _agent_step_presenters,
    _agent_submit_auto_repair,
    _agent_submit_repair,
)


def __getattr__(name: str):
    if name.startswith("_"):
        for module in _PRIVATE_COMPAT_MODULES:
            if hasattr(module, name):
                return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def register_agent_adapter_commands(
    init_app: typer.Typer,
    uninstall_app: typer.Typer,
    agent_app: typer.Typer,
) -> None:
    _agent_adapter_lifecycle_commands.register_agent_adapter_lifecycle_commands(init_app, uninstall_app)
    _agent_runtime_commands.register_agent_runtime_commands(agent_app)
