from __future__ import annotations

from pathlib import Path

import typer

from loopora.cli_agent_command_options import (
    AdapterRuntimeWorkdirOption,
    AttestRoleDispatchOption,
    CompactJsonOutputOption,
    ContextIdOption,
    EntrySourceOption,
    NoWebOption,
    ResultFileOption,
    RunIdOption,
    StepIdOption,
    effective_adapter_workdir,
)
from loopora.cli_agent_result_files import read_result_file_object
from loopora.cli_agent_runtime_actions import AgentSubmitErrorCliRequest, handle_agent_submit_error
from loopora.cli_agent_runtime_support import attach_web_url, resolved_entry_source
from loopora.cli_agent_step_presenters import _print_agent_step_result
from loopora.cli_agent_submit_auto_repair import read_result_json_with_auto_repair
from loopora.cli_agent_workdir_recovery import (
    AgentRuntimeWorkdirRecoveryRequest,
    exit_if_unusable_agent_runtime_workdir,
    exit_with_missing_agent_submit_result_file,
)
from loopora.cli_shared import JsonOutputOption, get_service
from loopora.service import LooporaError
from loopora.service_agent_native import AgentNativeStepSubmitRequest
from loopora.strategy_source import StrategySourceError


AGENT_SUBMIT_HELP_EPILOG = (
    "Submit is valid only after `agent next` or the managed entry returned a claimed step and result template. "
    "The main host Agent owns the result-file contents; do not submit ad hoc observations or reconstructed role output. "
    "Use --attest-role-dispatch only after the active target role agent returned that structured output."
)


def register_agent_submit_command(adapter_app: typer.Typer, *, adapter: str) -> None:
    @adapter_app.command("submit", epilog=AGENT_SUBMIT_HELP_EPILOG)
    def agent_submit(  # noqa: PLR0913 - native step submit exposes the stable Agent entry option surface.
        ctx: typer.Context,
        result_file: ResultFileOption = None,
        workdir: AdapterRuntimeWorkdirOption = Path(),
        context_id: ContextIdOption = "",
        run_id: RunIdOption = "",
        step_id: StepIdOption = "",
        entry_source: EntrySourceOption = "",
        *,
        attest_role_dispatch: AttestRoleDispatchOption = False,
        json_output: JsonOutputOption = False,
        compact_json_output: CompactJsonOutputOption = False,
        no_web: NoWebOption = False,
    ) -> None:
        """Submit a host Agent's structured step result back to Loopora Core."""
        workdir = effective_adapter_workdir(ctx, workdir)
        service = None
        resolved_source = resolved_entry_source(entry_source)
        result_payload: dict = {}
        host_dispatch: dict = {}
        auto_repair_actions: list[str] = []
        host_dispatch_attestation_source = ""
        recovery_request = AgentRuntimeWorkdirRecoveryRequest(
            adapter=adapter,
            workdir=workdir,
            action="submit",
            entry_source=resolved_source,
            json_output=json_output,
            compact_json_output=compact_json_output,
            result_file=result_file,
        )
        exit_if_unusable_agent_runtime_workdir(recovery_request)
        if result_file is None:
            exit_with_missing_agent_submit_result_file(recovery_request)
        try:
            read_result_file_object(result_file)
        except LooporaError as exc:
            try:
                service = get_service()
            except (LooporaError, StrategySourceError):
                service = None
            handle_agent_submit_error(
                exc,
                AgentSubmitErrorCliRequest(
                    service=service,
                    adapter=adapter,
                    context_id=context_id,
                    run_id=run_id,
                    entry_source=resolved_source,
                    result_file=result_file,
                    workdir=workdir,
                    json_output=json_output or compact_json_output,
                ),
            )
        try:
            service = get_service()
            result_payload, host_dispatch, auto_repair_actions, host_dispatch_attestation_source = read_result_json_with_auto_repair(
                result_file,
                service=service,
                run_id=run_id,
                workdir=workdir,
                attest_role_dispatch=attest_role_dispatch,
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
            if host_dispatch_attestation_source:
                result["host_dispatch_attestation_source"] = host_dispatch_attestation_source
            attach_web_url(result, path_key="run_path", url_key="run_url", no_web=no_web, workdir=workdir)
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
