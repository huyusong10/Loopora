from __future__ import annotations

import typer

from loopora.branding import APP_NAME
from loopora.cli_agent_adapter_commands import register_agent_adapter_commands
from loopora.cli_agent_command_options import AdapterGroupWorkdirOption
from loopora.cli_agent_group_previews import (
    agent_runtime_choice_preview,
    init_adapter_choice_preview,
    uninstall_adapter_choice_preview,
)
from loopora.cli_bundle_commands import BUNDLES_HELP_EPILOG, register_bundle_commands
from loopora.cli_diagnose_commands import DIAGNOSE_HELP_EPILOG, register_diagnose_commands
from loopora.cli_dev_commands import DEV_HELP_EPILOG, register_dev_commands
from loopora.cli_group_help import help_first_typer
from loopora.cli_runtime import set_service_factory, set_worker_spawner
from loopora.cli_shared import spawn_background_worker as _spawn_background_worker
from loopora.cli_loop_commands import LOOPS_HELP_EPILOG, register_loop_commands
from loopora.cli_orchestration_commands import ORCHESTRATIONS_HELP_EPILOG, register_orchestration_commands
from loopora.cli_prompt_commands import PROMPTS_HELP_EPILOG, register_prompt_commands
from loopora.cli_recovery_commands import recovery_help_epilog, register_recovery_commands
from loopora.cli_role_commands import ROLES_HELP_EPILOG, register_role_commands
from loopora.cli_root_commands import register_root_commands
from loopora.cli_shell_recovery import (
    AgentRuntimeAdapterCommandGroup,
    InitAdapterCommandGroup,
    LooporaRootHelpGroup,
    UninstallAdapterCommandGroup,
    _help_with_current_loopora_entry,
)
from loopora.cli_spec_commands import SPEC_HELP_EPILOG, register_spec_commands
from loopora.first_use_web_guidance import WEB_CREATION_CHOICE_SUMMARY
from loopora.service import create_service


def _current_service_factory(*, apply_startup_repairs: bool = True, storage_read_only: bool = False):
    if apply_startup_repairs and not storage_read_only:
        return create_service()
    return create_service(
        apply_startup_repairs=apply_startup_repairs,
        storage_read_only=storage_read_only,
    )


def _current_worker_spawner(service, run):
    return _spawn_background_worker(service, run)


set_service_factory(_current_service_factory)
set_worker_spawner(_current_worker_spawner)


FIRST_USE_WORKDIR_ARG = "'<project-dir>'"
FIRST_USE_WEB_CREATION_COMMAND = f"loopora serve --open --workdir {FIRST_USE_WORKDIR_ARG} --host 127.0.0.1 --port 8742"

ROOT_FIRST_USE_HELP = (
    f"{APP_NAME} CLI\n\n"
    "Start here:\n"
    "0. Before configuring an Agent or provider, run `loopora demo --open` to inspect one isolated completed Run.\n"
    '1. Run `loopora start --workdir "$PWD"` for a read-only next step.\n'
    '2. If fit is uncertain, use `loopora fit --workdir "$PWD" --task "..."` before setup.\n'
    '3. Outside an Agent session continue in Web; inside Codex, Claude Code, or OpenCode use `loopora init current --workdir "$PWD"`.\n'
    "Run only after READY review. Add `--details` to start or fit for every route and diagnostic.\n"
    'Existing work: `loopora status --workdir "$PWD"`. Readiness: `loopora doctor --workdir "$PWD"`. '
    'Recovery: `loopora recovery`. Support: `loopora support --workdir "$PWD"`.\n'
    "Chinese output: add `--language zh`. Contributor checks: run local checks with `loopora dev check`."
)

INIT_GROUP_HELP = (
    "Set up same-Agent project entries for /loopora-plan and /loopora-run.\n\n"
    "After setup, return to the Agent with the Loopora fit reason, task goal, fake-done risk, required evidence, "
    "judgment tradeoffs, and optional direct-path context.\n\n"
    "First-use path:\n"
    "If you are not sure this task needs a Loop, run `loopora fit` before installing.\n"
    "When fit is strong:\n"
    'Targetless setup commands below are preview-only; rerun `loopora init --workdir "$PWD"` from the target project '
    "to detect the current host, inspect explicit adapter fallbacks, and get concrete doctor and Web commands.\n"
    f"1. Same-Agent setup: from the current Agent session use `loopora init current --workdir {FIRST_USE_WORKDIR_ARG}` to install and confirm plan handoff; "
    f"if detection is unavailable or ambiguous, use `loopora init <agent> --workdir {FIRST_USE_WORKDIR_ARG}`.\n"
    f"2. Explicit-adapter readiness: `loopora doctor --workdir {FIRST_USE_WORKDIR_ARG}` confirms setup after the fallback or provides deeper diagnostics.\n"
    "3. After readiness passes, or when you already have reviewed material, choose one path:\n"
    "   Same-Agent path: return to that Agent and run `/loopora-plan`.\n"
    f"   Fit Guide/Web choices: use `{FIRST_USE_WEB_CREATION_COMMAND}` for {WEB_CREATION_CHOICE_SUMMARY}.\n"
    "   Plan-file/expert path: import a plan file or use manual expert mode in Web, then preview before "
    "creating or running.\n"
    "   Existing work path: inspect evidence, verdict state, residual risk, and next action in Web or `loopora loops`.\n"
    f"   Usage/setup help: use `loopora support --workdir {FIRST_USE_WORKDIR_ARG}` for safe support, public-material, and security-reporting routes.\n"
    "4. After the READY preview matches the task judgment:\n"
    "   Fit Guide/Web choices: create or run from Web, then review evidence, verdict state, residual risk, and next action there.\n"
    "   Same-Agent path: return to the same Agent session and run `/loopora-run`."
)


def _print_init_help_when_no_subcommand(ctx: typer.Context, workdir: AdapterGroupWorkdirOption = None) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if workdir is not None:
        typer.echo(init_adapter_choice_preview(workdir))
    else:
        typer.echo(ctx.get_help())
    raise typer.Exit


def _print_uninstall_help_when_no_subcommand(ctx: typer.Context, workdir: AdapterGroupWorkdirOption = None) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if workdir is not None:
        typer.echo(uninstall_adapter_choice_preview(workdir))
    else:
        typer.echo(ctx.get_help())
    raise typer.Exit


def _print_agent_help_when_no_subcommand(ctx: typer.Context, workdir: AdapterGroupWorkdirOption = None) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if workdir is not None:
        typer.echo(agent_runtime_choice_preview(workdir))
    else:
        typer.echo(ctx.get_help())
    raise typer.Exit


app = typer.Typer(
    cls=LooporaRootHelpGroup,
    help=_help_with_current_loopora_entry(ROOT_FIRST_USE_HELP),
)
loops_app = help_first_typer(help="Inspect and run saved Loops", epilog=_help_with_current_loopora_entry(LOOPS_HELP_EPILOG))
orchestrations_app = help_first_typer(
    help="Expert: create and inspect reusable run flows",
    epilog=_help_with_current_loopora_entry(ORCHESTRATIONS_HELP_EPILOG),
)
roles_app = help_first_typer(
    help="Expert: create and inspect reusable role definitions",
    epilog=_help_with_current_loopora_entry(ROLES_HELP_EPILOG),
)
bundles_app = help_first_typer(
    help="Import, export, and manage Loop plan files",
    epilog=_help_with_current_loopora_entry(BUNDLES_HELP_EPILOG),
)
spec_app = help_first_typer(
    help="Expert: work with Markdown Loop contracts",
    epilog=_help_with_current_loopora_entry(SPEC_HELP_EPILOG),
)
prompts_app = help_first_typer(
    help="Expert: inspect and validate Strategy Source prompt assets",
    epilog=_help_with_current_loopora_entry(PROMPTS_HELP_EPILOG),
)
diagnose_app = help_first_typer(
    help="Inspect local readiness, diagnostics, and safe historical repairs",
    epilog=_help_with_current_loopora_entry(DIAGNOSE_HELP_EPILOG),
)
recovery_app = help_first_typer(
    help="Create, verify, and safely restore private local-state archives",
    epilog=recovery_help_epilog(),
)
dev_app = help_first_typer(
    help="Developer: run local checks and reset incompatible development state",
    epilog=_help_with_current_loopora_entry(DEV_HELP_EPILOG),
)
init_app = help_first_typer(
    cls=InitAdapterCommandGroup,
    callback=_print_init_help_when_no_subcommand,
    help=_help_with_current_loopora_entry(INIT_GROUP_HELP),
)
uninstall_app = help_first_typer(
    cls=UninstallAdapterCommandGroup,
    callback=_print_uninstall_help_when_no_subcommand,
    help="Remove Loopora-managed Coding Agent project entries",
    epilog=_help_with_current_loopora_entry(
        'To remove one project entry, run `loopora uninstall <agent> --workdir "$PWD"` with codex, claude, or opencode. '
        'Then run `loopora doctor --workdir "$PWD"` to confirm readiness and remaining entries. '
        'Reinstall later with the same-Agent project entry matching your current host: `loopora init <agent> --workdir "$PWD"`; '
        "if the Agent still shows /loopora-plan or /loopora-run, refresh or restart it."
    ),
)
agent_app = help_first_typer(
    cls=AgentRuntimeAdapterCommandGroup,
    callback=_print_agent_help_when_no_subcommand,
    help="Internal runtime used by /loopora-plan and /loopora-run project entries",
    epilog=_help_with_current_loopora_entry(
        "This group is normally called by Loopora-managed Agent entries, not by first-use shell workflows. "
        'If you are choosing how to start, run `loopora start` first, then rerun `loopora start --workdir "$PWD"` '
        "from the target project before copying Web/init/doctor route commands; use `loopora fit` when fit is uncertain. "
        "Outside an Agent session, use the Fit Guide/Web choices printed by the target-project start guide. "
        'Same-Agent setup starts with `loopora init --workdir "$PWD"` from the target project so you can choose '
        'the matching current-host entry, then `loopora doctor --workdir "$PWD"`; '
        "after readiness passes, return to that Agent for `/loopora-plan` and `/loopora-run`. "
        'Use `loopora agent <agent> check --workdir "$PWD"` only when you need a CLI diagnostic for the installed entry.'
    ),
)

app.add_typer(init_app, name="init")
app.add_typer(uninstall_app, name="uninstall")
app.add_typer(loops_app, name="loops")
app.add_typer(orchestrations_app, name="orchestrations", hidden=True)
app.add_typer(roles_app, name="roles", hidden=True)
app.add_typer(bundles_app, name="bundles")
app.add_typer(spec_app, name="spec", hidden=True)
app.add_typer(prompts_app, name="prompts", hidden=True)
app.add_typer(diagnose_app, name="diagnose")
app.add_typer(recovery_app, name="recovery")
app.add_typer(dev_app, name="dev", hidden=True)
app.add_typer(agent_app, name="agent", hidden=True)

register_root_commands(app)
register_loop_commands(loops_app)
register_orchestration_commands(orchestrations_app)
register_role_commands(roles_app)
register_bundle_commands(bundles_app)
register_spec_commands(spec_app)
register_prompt_commands(prompts_app)
register_diagnose_commands(diagnose_app)
register_recovery_commands(recovery_app)
register_dev_commands(dev_app)
register_agent_adapter_commands(init_app, uninstall_app, agent_app)

__all__ = ["_spawn_background_worker", "app", "create_service"]
