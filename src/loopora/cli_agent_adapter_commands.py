from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from loopora import cli_agent_native as _agent_native
from loopora import cli_agent_step_presenters as _agent_step_presenters
from loopora import cli_agent_submit_repair as _agent_submit_repair
from loopora.cli_agent_native import (
    _attach_web_url as _attach_web_url,
    _handle_adapter_install_conflict as _handle_adapter_install_conflict,
    _print_adapter_check_result as _print_adapter_check_result,
    _print_adapter_mutation_result as _print_adapter_mutation_result,
    _print_agent_gen_result as _print_agent_gen_result,
    _print_agent_loop_unready_guidance as _print_agent_loop_unready_guidance,
    _print_agent_next_recovery_guidance as _print_agent_next_recovery_guidance,
    _print_agent_plan_recovery_guidance as _print_agent_plan_recovery_guidance,
    _read_result_json as _read_result_json,
    _resolved_entry_source as _resolved_entry_source,
    _spawn_agent_loop_worker_if_needed as _spawn_agent_loop_worker_if_needed,
)
from loopora.cli_agent_step_presenters import (
    _print_agent_loop_result as _print_agent_loop_result,
    _print_agent_next_result as _print_agent_next_result,
    _print_agent_step_result as _print_agent_step_result,
)
from loopora.cli_agent_submit_repair import _print_agent_submit_repair_guidance as _print_agent_submit_repair_guidance
from loopora.cli_shared import JsonOutputOption, get_service, handle_error
from loopora.service import LooporaError
from loopora.service_agent_native import AgentNativeStepClaimRequest, AgentNativeStepSubmitRequest
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.service_types import LooporaConflictError
from loopora.workflows import WorkflowError

AdapterWorkdirOption = Annotated[
    Path,
    typer.Option(
        "--workdir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Project directory where the Coding Agent will work.",
    ),
]
ContextIdOption = Annotated[
    str,
    typer.Option("--context-id", help="Optional host session/thread identity. Defaults to Loopora, Codex, Claude Code, or OpenCode session env vars, then workdir."),
]
EntrySourceOption = Annotated[
    str,
    typer.Option("--entry-source", hidden=True, help="Internal marker for Loopora-managed Agent entry provenance."),
]
BundleFileOption = Annotated[
    Path | None,
    typer.Option(
        "--bundle-file",
        "--plan-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Candidate Loop plan file produced by the Coding Agent.",
    ),
]
ResultFileOption = Annotated[
    Path,
    typer.Option("--result-file", file_okay=True, dir_okay=False, help="JSON result produced by the host Agent for the claimed Loopora step."),
]
RunIdOption = Annotated[str, typer.Option("--run-id", help="Optional Loopora run id. Defaults to the run bound to the current host session/workdir.")]
StepIdOption = Annotated[str, typer.Option("--step-id", help="Loopora step id being submitted.")]
AdapterMessageOption = Annotated[
    str,
    typer.Option("--message", help="Short task summary for the Loop preview; required for Agent-first traceability."),
]
NoWebOption = Annotated[bool, typer.Option("--no-web", hidden=True, help="Skip local Web service startup.")]
CheckOption = Annotated[bool, typer.Option("--check", help="Check the Loopora Agent entry without installing or repairing files.")]
SourceOptionIdOption = Annotated[str, typer.Option("--source-option-id", help="Recoverable Loopora context option id selected by the user.")]


def __getattr__(name: str):
    if name.startswith("_") and hasattr(_agent_native, name):
        return getattr(_agent_native, name)
    if name.startswith("_") and hasattr(_agent_step_presenters, name):
        return getattr(_agent_step_presenters, name)
    if name.startswith("_") and hasattr(_agent_submit_repair, name):
        return getattr(_agent_submit_repair, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def register_agent_adapter_commands(
    init_app: typer.Typer,
    uninstall_app: typer.Typer,
    agent_app: typer.Typer,
) -> None:
    _register_init_commands(init_app)
    _register_uninstall_commands(uninstall_app)
    _register_agent_runtime_commands(agent_app)


def _register_init_commands(init_app: typer.Typer) -> None:
    @init_app.command("codex")
    def init_codex(workdir: AdapterWorkdirOption = Path("."), check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
        """Install or update the Codex project entry for task-judgment first use.

        Then return to Codex with the task goal, fake-done risk, and required evidence.
        Run /loopora-plan, review the READY Loop preview, and run /loopora-run in the same Agent session.
        """
        _install_adapter("codex", workdir=workdir, check=check, json_output=json_output)

    @init_app.command("claude")
    def init_claude(workdir: AdapterWorkdirOption = Path("."), check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
        """Install or update the Claude Code project entry for task-judgment first use.

        Then return to Claude Code with the task goal, fake-done risk, and required evidence.
        Run /loopora-plan, review the READY Loop preview, and run /loopora-run in the same Agent session.
        """
        _install_adapter("claude", workdir=workdir, check=check, json_output=json_output)

    @init_app.command("opencode")
    def init_opencode(workdir: AdapterWorkdirOption = Path("."), check: CheckOption = False, json_output: JsonOutputOption = False) -> None:
        """Install or update the OpenCode project entry for task-judgment first use.

        Then return to OpenCode with the task goal, fake-done risk, and required evidence.
        Run /loopora-plan, review the READY Loop preview, and run /loopora-run in the same Agent session.
        """
        _install_adapter("opencode", workdir=workdir, check=check, json_output=json_output)


def _install_adapter(adapter: str, *, workdir: Path, check: bool, json_output: bool) -> None:
    try:
        if check:
            _check_adapter(adapter, workdir=workdir, json_output=json_output)
            return
        result = get_service().install_agent_adapter(adapter, workdir=workdir)
        _print_adapter_mutation_result(result, action="installed", json_output=json_output)
    except LooporaConflictError as exc:
        _handle_adapter_install_conflict(adapter, workdir=workdir, exc=exc, json_output=json_output)
    except LooporaError as exc:
        handle_error(exc)


def _check_adapter(adapter: str, *, workdir: Path, json_output: bool) -> None:
    try:
        result = get_service().check_agent_adapter(adapter, workdir=workdir)
        _print_adapter_check_result(result, json_output=json_output)
        if result.get("check_status") != "pass":
            raise typer.Exit(code=1)
    except LooporaError as exc:
        handle_error(exc)


def _register_uninstall_commands(uninstall_app: typer.Typer) -> None:
    @uninstall_app.command("codex")
    def uninstall_codex(workdir: AdapterWorkdirOption = Path("."), json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed Codex project entry."""
        _uninstall_adapter("codex", workdir=workdir, json_output=json_output)

    @uninstall_app.command("claude")
    def uninstall_claude(workdir: AdapterWorkdirOption = Path("."), json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed Claude Code project entry."""
        _uninstall_adapter("claude", workdir=workdir, json_output=json_output)

    @uninstall_app.command("opencode")
    def uninstall_opencode(workdir: AdapterWorkdirOption = Path("."), json_output: JsonOutputOption = False) -> None:
        """Remove the Loopora-managed OpenCode project entry."""
        _uninstall_adapter("opencode", workdir=workdir, json_output=json_output)


def _uninstall_adapter(adapter: str, *, workdir: Path, json_output: bool) -> None:
    try:
        result = get_service().uninstall_agent_adapter(adapter, workdir=workdir)
        _print_adapter_mutation_result(result, action="uninstalled", json_output=json_output)
    except LooporaError as exc:
        handle_error(exc)


def _register_agent_runtime_commands(agent_app: typer.Typer) -> None:
    _register_agent_runtime_for(agent_app, adapter="codex", help_text="Internal Codex runtime used by Loopora project entries")
    _register_agent_runtime_for(agent_app, adapter="claude", help_text="Internal Claude Code runtime used by Loopora project entries")
    _register_agent_runtime_for(agent_app, adapter="opencode", help_text="Internal OpenCode runtime used by Loopora project entries")


def _register_agent_runtime_for(agent_app: typer.Typer, *, adapter: str, help_text: str) -> None:
    adapter_app = typer.Typer(help=help_text)
    agent_app.add_typer(adapter_app, name=adapter)

    @adapter_app.command("plan")
    def agent_plan(
        workdir: AdapterWorkdirOption = Path("."),
        message: AdapterMessageOption = "",
        bundle_file: BundleFileOption = None,
        context_id: ContextIdOption = "",
        entry_source: EntrySourceOption = "",
        json_output: JsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Validate a generated Loop plan and return the Loop preview URL."""
        try:
            request = AgentBundleCandidateRequest(
                adapter=adapter,
                workdir=workdir,
                message=message,
                bundle_file=bundle_file,
                context_id=context_id,
                entry_source=_resolved_entry_source(entry_source),
            )
            result = get_service().create_agent_bundle_candidate(request)
            _attach_web_url(result, path_key="preview_path", url_key="preview_url", no_web=no_web)
            _print_agent_gen_result(result, json_output=json_output)
        except (LooporaError, WorkflowError) as exc:
            _handle_agent_plan_error(
                exc,
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                entry_source=_resolved_entry_source(entry_source),
                json_output=json_output,
            )

    @adapter_app.command("run")
    def agent_run(
        workdir: AdapterWorkdirOption = Path("."),
        context_id: ContextIdOption = "",
        source_option_id: SourceOptionIdOption = "",
        entry_source: EntrySourceOption = "",
        json_output: JsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Start or reuse the Loopora run associated with the current ready Loop preview."""
        service = None
        resolved_entry_source = _resolved_entry_source(entry_source)
        try:
            service = get_service()
            result = _start_agent_loop_from_cli(
                service,
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                source_option_id=source_option_id,
                entry_source=resolved_entry_source,
            )
            _spawn_agent_loop_worker_if_needed(service, result)
            _attach_web_url(result, path_key="run_path", url_key="run_url", no_web=no_web)
            _print_agent_loop_result(result, json_output=json_output)
        except (LooporaError, WorkflowError) as exc:
            if _print_agent_loop_unready_guidance(
                exc,
                service=service,
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                entry_source=resolved_entry_source,
                no_web=no_web,
                json_output=json_output,
            ):
                raise typer.Exit(code=1) from exc
            handle_error(exc)

    _register_agent_check_command(adapter_app, adapter=adapter)

    @adapter_app.command("next")
    def agent_next(
        workdir: AdapterWorkdirOption = Path("."),
        context_id: ContextIdOption = "",
        run_id: RunIdOption = "",
        entry_source: EntrySourceOption = "",
        json_output: JsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Claim the next Loopora step capsule for the host Agent to execute natively."""
        _claim_agent_next_from_cli(
            adapter=adapter,
            workdir=workdir,
            context_id=context_id,
            run_id=run_id,
            entry_source=entry_source,
            json_output=json_output,
            no_web=no_web,
        )

    @adapter_app.command("submit")
    def agent_submit(
        result_file: ResultFileOption,
        workdir: AdapterWorkdirOption = Path("."),
        context_id: ContextIdOption = "",
        run_id: RunIdOption = "",
        step_id: StepIdOption = "",
        entry_source: EntrySourceOption = "",
        json_output: JsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Submit a host Agent's structured step result back to Loopora Core."""
        service = get_service()
        resolved_entry_source = _resolved_entry_source(entry_source)
        result_payload: dict = {}
        host_dispatch: dict = {}
        try:
            result_payload, host_dispatch = _read_result_json(result_file)
            result = service.submit_agent_native_step(
                AgentNativeStepSubmitRequest(
                    adapter=adapter,
                    workdir=workdir,
                    context_id=context_id,
                    run_id=run_id,
                    step_id=step_id,
                    output=result_payload,
                    host_dispatch=host_dispatch,
                    entry_source=resolved_entry_source,
                )
            )
            _attach_web_url(result, path_key="run_path", url_key="run_url", no_web=no_web)
            _print_agent_step_result(result, json_output=json_output)
        except (LooporaError, WorkflowError) as exc:
            _handle_agent_submit_error(
                exc,
                service=service,
                adapter=adapter,
                context_id=context_id,
                run_id=run_id or str(host_dispatch.get("run_id") or ""),
                entry_source=resolved_entry_source,
                result_file=result_file,
                workdir=workdir,
                json_output=json_output,
            )


def _register_agent_check_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    @adapter_app.command("check")
    def agent_check(workdir: AdapterWorkdirOption = Path("."), json_output: JsonOutputOption = False) -> None:
        """Check the Loopora-managed project entry for this Agent adapter."""
        _check_adapter(adapter, workdir=workdir, json_output=json_output)


def _claim_agent_next_from_cli(
    *,
    adapter: str,
    workdir: Path,
    context_id: str,
    run_id: str,
    entry_source: str,
    json_output: bool,
    no_web: bool,
) -> None:
    service = get_service()
    resolved_entry_source = _resolved_entry_source(entry_source)
    try:
        result = service.claim_agent_native_step(
            AgentNativeStepClaimRequest(
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                run_id=run_id,
                entry_source=resolved_entry_source,
            )
        )
        _attach_web_url(result, path_key="run_path", url_key="run_url", no_web=no_web)
        _print_agent_next_result(result, json_output=json_output)
    except (LooporaError, WorkflowError) as exc:
        if _print_agent_next_recovery_guidance(
            exc,
            service=service,
            adapter=adapter,
            workdir=workdir,
            context_id=context_id,
            entry_source=resolved_entry_source,
            no_web=no_web,
            json_output=json_output,
        ):
            raise typer.Exit(code=1) from exc
        handle_error(exc)


def _handle_agent_submit_error(
    exc: LooporaError | WorkflowError,
    *,
    service,
    adapter: str,
    context_id: str,
    run_id: str,
    entry_source: str,
    result_file: Path,
    workdir: Path,
    json_output: bool,
) -> None:
    if _print_agent_submit_repair_guidance(
        exc,
        service=service,
        adapter=adapter,
        context_id=context_id,
        run_id=run_id,
        entry_source=entry_source,
        result_file=result_file,
        workdir=workdir,
        json_output=json_output,
    ):
        raise typer.Exit(code=1) from exc
    handle_error(exc)


def _handle_agent_plan_error(
    exc: LooporaError | WorkflowError,
    *,
    adapter: str,
    workdir: Path,
    context_id: str,
    entry_source: str,
    json_output: bool,
) -> None:
    if _print_agent_plan_recovery_guidance(
        exc,
        adapter=adapter,
        workdir=workdir,
        context_id=context_id,
        entry_source=entry_source,
        json_output=json_output,
    ):
        raise typer.Exit(code=1) from exc
    handle_error(exc)


def _start_agent_loop_from_cli(
    service,
    *,
    adapter: str,
    workdir: Path,
    context_id: str,
    source_option_id: str,
    entry_source: str,
) -> dict:
    start_kwargs = {
        "workdir": workdir,
        "context_id": context_id,
        "entry_source": entry_source,
        "execute_async": False,
    }
    if source_option_id:
        start_kwargs["source_option_id"] = source_option_id
    return service.start_agent_loop(adapter, **start_kwargs)


def _adapter_label(adapter: str) -> str:
    return {
        "codex": "Codex",
        "claude": "Claude Code",
        "opencode": "OpenCode",
    }.get(adapter, adapter or "Agent")
