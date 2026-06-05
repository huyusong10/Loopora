from __future__ import annotations

from pathlib import Path

import typer

from loopora import cli_agent_adapter_lifecycle_commands as _agent_adapter_lifecycle_commands
from loopora.cli_agent_command_options import (
    AdapterMessageOption,
    AdapterWorkdirOption,
    BundleFileOption,
    CompactJsonOutputOption,
    ContextIdOption,
    EntrySourceOption,
    NextStepIdCompatOption,
    NoWebOption,
    ResultFileOption,
    RunIdOption,
    SourceOptionIdOption,
    StepIdOption,
)
from loopora.cli_agent_plan_output import _print_agent_gen_result
from loopora.cli_agent_recovery import _print_agent_loop_unready_guidance
from loopora.cli_agent_runtime_actions import (
    AgentLoopStartCliRequest,
    AgentNextCliRequest,
    AgentPlanErrorCliRequest,
    AgentSubmitErrorCliRequest,
    claim_agent_next_from_cli,
    handle_agent_plan_error,
    handle_agent_submit_error,
    start_agent_loop_from_cli,
)
from loopora.cli_agent_runtime_support import (
    attach_web_url,
    resolved_entry_source,
    spawn_agent_loop_worker_if_needed,
)
from loopora.cli_agent_step_presenters import _print_agent_loop_result, _print_agent_step_result
from loopora.cli_agent_submit_auto_repair import read_result_json_with_auto_repair
from loopora.cli_shared import JsonOutputOption, get_service, handle_error
from loopora.service import LooporaError
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.service_agent_native import AgentNativeStepSubmitRequest
from loopora.strategy_source import StrategySourceError


def register_agent_runtime_commands(agent_app: typer.Typer) -> None:
    _register_agent_runtime_for(agent_app, adapter="codex", help_text="Internal Codex runtime used by Loopora project entries")
    _register_agent_runtime_for(agent_app, adapter="claude", help_text="Internal Claude Code runtime used by Loopora project entries")
    _register_agent_runtime_for(agent_app, adapter="opencode", help_text="Internal OpenCode runtime used by Loopora project entries")


def _register_agent_runtime_for(agent_app: typer.Typer, *, adapter: str, help_text: str) -> None:
    adapter_app = typer.Typer(help=help_text)
    agent_app.add_typer(adapter_app, name=adapter)
    _agent_adapter_lifecycle_commands.register_agent_check_command(adapter_app, adapter=adapter)

    @adapter_app.command("plan")
    def agent_plan(
        workdir: AdapterWorkdirOption = Path(),
        message: AdapterMessageOption = "",
        bundle_file: BundleFileOption = None,
        context_id: ContextIdOption = "",
        entry_source: EntrySourceOption = "",
        *,
        json_output: JsonOutputOption = False,
        compact_json_output: CompactJsonOutputOption = False,
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
                entry_source=resolved_entry_source(entry_source),
            )
            result = get_service().create_agent_bundle_candidate(request)
            attach_web_url(result, path_key="preview_path", url_key="preview_url", no_web=no_web)
            _print_agent_gen_result(result, json_output=json_output, compact_json_output=compact_json_output)
        except (LooporaError, StrategySourceError) as exc:
            handle_agent_plan_error(
                exc,
                AgentPlanErrorCliRequest(
                    adapter=adapter,
                    workdir=workdir,
                    context_id=context_id,
                    entry_source=resolved_entry_source(entry_source),
                    json_output=json_output or compact_json_output,
                ),
            )

    @adapter_app.command("run")
    def agent_run(
        workdir: AdapterWorkdirOption = Path(),
        context_id: ContextIdOption = "",
        source_option_id: SourceOptionIdOption = "",
        entry_source: EntrySourceOption = "",
        *,
        json_output: JsonOutputOption = False,
        compact_json_output: CompactJsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Start or reuse the Loopora run associated with the current ready Loop preview."""
        service = None
        resolved_source = resolved_entry_source(entry_source)
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
            attach_web_url(result, path_key="run_path", url_key="run_url", no_web=no_web)
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
                raise typer.Exit(code=1) from exc
            handle_error(exc)

    @adapter_app.command("next")
    def agent_next(
        workdir: AdapterWorkdirOption = Path(),
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
        claim_agent_next_from_cli(
            AgentNextCliRequest(
                adapter=adapter,
                workdir=workdir,
                context_id=context_id,
                run_id=run_id,
                entry_source=entry_source,
                json_output=json_output,
                compact_json_output=compact_json_output,
                no_web=no_web,
            ),
        )

    @adapter_app.command("submit")
    def agent_submit(
        result_file: ResultFileOption,
        workdir: AdapterWorkdirOption = Path(),
        context_id: ContextIdOption = "",
        run_id: RunIdOption = "",
        step_id: StepIdOption = "",
        entry_source: EntrySourceOption = "",
        *,
        json_output: JsonOutputOption = False,
        compact_json_output: CompactJsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Submit a host Agent's structured step result back to Loopora Core."""
        service = get_service()
        resolved_source = resolved_entry_source(entry_source)
        result_payload: dict = {}
        host_dispatch: dict = {}
        auto_repair_actions: list[str] = []
        try:
            result_payload, host_dispatch, auto_repair_actions = read_result_json_with_auto_repair(
                result_file,
                service=service,
                run_id=run_id,
                workdir=workdir,
            )
            result = service.submit_agent_native_step(
                AgentNativeStepSubmitRequest(
                    adapter=adapter,
                    workdir=workdir,
                    context_id=context_id,
                    run_id=run_id,
                    step_id=step_id,
                    output=result_payload,
                    host_dispatch=host_dispatch,
                    entry_source=resolved_source,
                )
            )
            if auto_repair_actions:
                result["auto_repair_applied"] = True
                result["auto_repair_actions"] = auto_repair_actions
            attach_web_url(result, path_key="run_path", url_key="run_url", no_web=no_web)
            _print_agent_step_result(result, json_output=json_output, compact_json_output=compact_json_output)
        except (LooporaError, StrategySourceError) as exc:
            handle_agent_submit_error(
                exc,
                AgentSubmitErrorCliRequest(
                    service=service,
                    adapter=adapter,
                    context_id=context_id,
                    run_id=run_id or str(host_dispatch.get("run_id") or ""),
                    entry_source=resolved_source,
                    result_file=result_file,
                    workdir=workdir,
                    json_output=json_output or compact_json_output,
                    auto_repair_actions=auto_repair_actions,
                ),
            )
