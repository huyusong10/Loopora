from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from loopora.agent_adapter_command_prefix import rewrite_loopora_help_commands
from loopora.cli_dev_check_output import (
    print_dev_check_progress as _print_dev_check_progress,
    print_dev_check_result as _print_dev_check_result,
)
from loopora.cli_dev_check_recovery import (
    DEV_COMMAND_ERROR_SCHEMA_VERSION as _DEV_COMMAND_ERROR_SCHEMA_VERSION,
    dev_check_cli_result as _dev_check_cli_result,
    handle_dev_command_error as _handle_dev_command_error,
)
from loopora.cli_dev_pr_evidence import (
    dedupe_text as _dedupe_text,
    dev_check_focused_ran_tokens as _dev_check_focused_ran_tokens,
    dev_check_pr_evidence_payload as _dev_check_pr_evidence_payload,
    dev_check_selection_tokens as _dev_check_selection_tokens,
    print_dev_check_pr_evidence_summary as _print_dev_check_pr_evidence_summary,
)
from loopora.cli_dev_release_plan import (
    DevReleaseSupportedStatus,
    dev_release_plan_payload as _dev_release_plan_payload,
    print_dev_release_plan as _print_dev_release_plan,
)
from loopora.cli_dev_reset_output import (
    DEV_RESET_SUMMARY_SCHEMA_VERSION as _DEV_RESET_SUMMARY_SCHEMA_VERSION,
    dev_reset_json_payload as _dev_reset_json_payload,
    print_dev_reset_result as _print_dev_reset_result,
)
from loopora.cli_shared import JsonOutputOption, echo_json
from loopora.dev_check import DEFAULT_FAST_PROFILE, FOCUSED_PROFILE, focused_check_selection_choices, focused_check_selection_help, run_dev_check
from loopora.dev_reset import dev_reset_loopora_state
from loopora.fit_guidance import normalize_fit_guidance_language
from loopora.service_types import LooporaError

DEV_HELP_EPILOG = (
    "Contributor flow: use `loopora dev check --list` to see the default-fast gate and focused guides, "
    "run `loopora dev check --focused recommended` for changed-file evidence before the final default-fast gate, "
    "use `loopora dev release-plan` for maintainer-owned release evidence planning, and use `loopora dev reset` "
    "only as an explicit preview/apply recovery for incompatible local development state."
)
DEV_CHECK_HELP_EPILOG = (
    "For PR work, start with `--list` or `--focused recommended` to name the focused guide IDs for the touched "
    "stable boundary, then run the default-fast gate before finishing. Pass changed paths positionally or with "
    "`--changed-file` when Git detection is unavailable or you need bounded scope evidence; `--json` keeps the same "
    "recommendations and next actions for automation, and `--pr-evidence` prints a copyable PR summary. Use `--focused-ran <guide-id>` on "
    "remaining focused or final evidence commands when focused guides already passed in a separate run."
)
DEV_RESET_HELP_EPILOG = (
    "Reset is a recovery path, not routine cleanup: the default run is a no-mutation preview, `--scope app` "
    "limits recovery to local App state, and deletion requires rerunning the printed apply command with `--yes`. "
    "Before deleting useful local history, create and inspect a private exact-path archive with "
    "`loopora recovery create --workdir <project>`. "
    "After any apply/no-op, return to `loopora doctor --workdir <project>` before opening Web or running "
    "`/loopora-plan`."
)

DevResetWorkdirOption = Annotated[
    Path,
    typer.Option(
        "--workdir",
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Project directory whose development Loopora state should be reset.",
    ),
]
DevCheckWorkdirOption = Annotated[
    Path,
    typer.Option(
        "--workdir",
        exists=False,
        file_okay=True,
        dir_okay=True,
        help="Project directory where the default-fast verification gate should run.",
    ),
]
DevResetYesOption = Annotated[
    bool,
    typer.Option("--yes", help="Actually delete the planned Loopora development state. Without this flag the command is a dry run."),
]
DevResetLanguageOption = Annotated[
    str,
    typer.Option(
        "--language",
        help="Plain reset-recovery language: en or zh; common aliases like en-US and zh-CN are normalized.",
    ),
]
DevCheckProfileOption = Annotated[
    str,
    typer.Option(
        "--profile",
        help=(
            "Advanced profile selector. Keep default-fast for the full local gate; "
            "use --focused to run focused checks."
        ),
    ),
]
DevCheckListOption = Annotated[
    bool,
    typer.Option("--list", help="List default-fast steps and focused check guidance without running commands."),
]
DevCheckFocusedOption = Annotated[
    list[str] | None,
    typer.Option(
        "--focused",
        help=focused_check_selection_help(),
    ),
]
DevCheckChangedFileOption = Annotated[
    list[str] | None,
    typer.Option(
        "--changed-file",
        help=(
            "Changed path to use for focused check recommendations instead of Git detection. "
            "Repeat for multiple paths."
        ),
    ),
]
DevCheckChangedPathArgument = Annotated[
    list[str] | None,
    typer.Argument(
        help=(
            "Changed paths to use for focused check recommendations instead of Git detection. "
            "Equivalent to repeating --changed-file."
        ),
    ),
]
DevCheckPrEvidenceOption = Annotated[
    bool,
    typer.Option(
        "--pr-evidence",
        help="Print a copyable PR evidence summary instead of the full plain report.",
    ),
]
DevCheckFocusedRanOption = Annotated[
    list[str] | None,
    typer.Option(
        "--focused-ran",
        help=(
            "Focused guide IDs already run for remaining focused or final PR evidence. Ignored by --list decision evidence. "
            "Accepts guide IDs, recommended, or all; repeat or comma-separate values."
        ),
    ),
]

DEV_RESET_SUMMARY_SCHEMA_VERSION = _DEV_RESET_SUMMARY_SCHEMA_VERSION
DEV_COMMAND_ERROR_SCHEMA_VERSION = _DEV_COMMAND_ERROR_SCHEMA_VERSION


class DevResetScope(StrEnum):
    all = "all"
    app = "app"


DevResetScopeOption = Annotated[
    DevResetScope,
    typer.Option(
        "--scope",
        help="Reset scope: app clears only the local App database; all also clears project Loopora state and managed entries.",
    ),
]
DevReleaseCandidateOption = Annotated[
    str,
    typer.Option("--candidate", help="Release candidate version or tag being planned."),
]
DevReleaseProbeRefOption = Annotated[
    str,
    typer.Option(
        "--probe-ref",
        help="Git branch or tag ref used when dispatching release real probes. Defaults to --candidate.",
    ),
]
DevReleaseSupportedStatusOption = Annotated[
    DevReleaseSupportedStatus,
    typer.Option(
        "--supported-status",
        help="Maintainer intent for SECURITY.md support status: supported, unsupported, or undecided.",
    ),
]


def register_dev_commands(dev_app: typer.Typer) -> None:  # noqa: C901 - Typer command registration keeps public dev subcommands together.
    @dev_app.command("check", epilog=DEV_CHECK_HELP_EPILOG)
    def check(  # noqa: PLR0913 - dev-check CLI keeps public options explicit.
        workdir: DevCheckWorkdirOption = Path(),
        profile: DevCheckProfileOption = DEFAULT_FAST_PROFILE,
        changed_paths: DevCheckChangedPathArgument = None,
        *,
        list_only: DevCheckListOption = False,
        focused: DevCheckFocusedOption = None,
        changed_files: DevCheckChangedFileOption = None,
        pr_evidence: DevCheckPrEvidenceOption = False,
        focused_ran: DevCheckFocusedRanOption = None,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Run the local default-fast verification gate."""
        try:
            focused_selection = _dev_check_focused_selection(focused)
            effective_changed_files = _combined_dev_check_changed_files(changed_files, changed_paths)
            _validate_dev_check_focused_ran(focused_ran)
            focused_ran_for_report = (
                focused_ran
                if not list_only and (pr_evidence or focused_selection or profile == FOCUSED_PROFILE)
                else None
            )
            progress_reporter = None if json_output or list_only else _print_dev_check_progress
            result = run_dev_check(
                workdir=workdir,
                profile=profile,
                list_only=list_only,
                focused=focused_selection,
                changed_files=effective_changed_files,
                focused_ran=focused_ran_for_report,
                progress_reporter=progress_reporter,
            )
            result = _dev_check_cli_result(result)
        except (LooporaError, OSError) as exc:
            _handle_dev_command_error(
                exc,
                json_output=json_output,
                command="check",
                workdir=workdir,
                changed_files=_combined_dev_check_changed_files(changed_files, changed_paths),
            )
            return
        if pr_evidence:
            result["pr_evidence_summary"] = _dev_check_pr_evidence_payload(result, focused_ran=focused_ran)
        if json_output:
            echo_json(result)
        elif pr_evidence:
            _print_dev_check_pr_evidence_summary(result)
        else:
            _print_dev_check_result(result)
        if result.get("status") == "fail":
            raise typer.Exit(code=1)

    @dev_app.command("release-plan")
    def release_plan(
        workdir: DevCheckWorkdirOption = Path(),
        candidate: DevReleaseCandidateOption = "",
        probe_ref: DevReleaseProbeRefOption = "",
        supported_status: DevReleaseSupportedStatusOption = DevReleaseSupportedStatus.undecided,
        *,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Print a read-only release-readiness evidence plan."""
        payload = _dev_release_plan_payload(
            workdir=workdir,
            candidate=candidate,
            probe_ref=probe_ref,
            supported_status=supported_status.value,
        )
        if json_output:
            echo_json(payload)
            return
        _print_dev_release_plan(payload)

    @dev_app.command("reset", epilog=rewrite_loopora_help_commands(DEV_RESET_HELP_EPILOG))
    def reset(
        workdir: DevResetWorkdirOption = Path(),
        scope: DevResetScopeOption = DevResetScope.all,
        *,
        yes: DevResetYesOption = False,
        language: DevResetLanguageOption = "en",
        json_output: JsonOutputOption = False,
    ) -> None:
        """Preview or reset incompatible v3 development state for one project."""
        try:
            language = normalize_fit_guidance_language(language)
        except ValueError as exc:
            if json_output:
                _handle_dev_command_error(
                    ValueError(f"invalid --language: {exc}"),
                    json_output=True,
                    command="reset",
                    workdir=workdir,
                )
                return
            typer.echo(f"invalid --language: {exc}", err=True)
            raise typer.Exit(code=2) from exc
        try:
            result = dev_reset_loopora_state(workdir=workdir, apply=yes, scope=scope.value)
        except (LooporaError, OSError, ValueError) as exc:
            _handle_dev_command_error(exc, json_output=json_output, command="reset", workdir=workdir)
            return
        if json_output:
            echo_json(_dev_reset_json_payload(result))
            return
        _print_dev_reset_result(result, language=language)


def _validate_dev_check_focused_ran(values: list[str] | None) -> None:
    choices = set(focused_check_selection_choices())
    tokens = _dev_check_focused_ran_tokens(values)
    unsupported = next((token for token in tokens if token not in choices), "")
    if unsupported:
        expected = ", ".join(focused_check_selection_choices())
        raise LooporaError(f"unsupported focused check guide: {unsupported!r}. Expected one of: {expected}")


def _dev_check_focused_selection(values: list[str] | None) -> str:
    return ",".join(_dev_check_selection_tokens(values))


def _combined_dev_check_changed_files(options: list[str] | None, arguments: list[str] | None) -> list[str] | None:
    values = _dedupe_text([*list(options or []), *list(arguments or [])])
    return values or None
