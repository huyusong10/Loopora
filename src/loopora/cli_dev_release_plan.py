from __future__ import annotations

from enum import StrEnum
from pathlib import Path
import shlex

import typer

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.cli_dev_check_recovery import dev_check_recovery_command
from loopora.dev_check_command_projection import copyable_dev_check_command
from loopora.workdir_inputs import workdir_path_state

DEV_RELEASE_PLAN_SCHEMA_VERSION = 1


class DevReleaseSupportedStatus(StrEnum):
    undecided = "undecided"
    supported = "supported"
    unsupported = "unsupported"


def dev_release_plan_payload(*, workdir: Path, candidate: str, probe_ref: str, supported_status: str) -> dict:
    workdir_state = workdir_path_state(workdir)
    workdir_status = str(workdir_state.get("status") or "unavailable")
    workdir_text = str(workdir_state.get("workdir") or workdir)
    resolved_workdir = Path(workdir_text).resolve(strict=False) if workdir_text else workdir.resolve(strict=False)
    candidate_text = str(candidate or "").strip()
    supplied_probe_ref = str(probe_ref or "").strip()
    release_probe_ref = supplied_probe_ref or candidate_text
    probe_ref_source = "provided" if supplied_probe_ref else "candidate"
    status = str(supported_status or DevReleaseSupportedStatus.undecided.value).strip() or DevReleaseSupportedStatus.undecided.value
    blockers = [
        *([] if workdir_status == "ready" else [f"workdir_{workdir_status}"]),
        *([] if candidate_text else ["candidate_required"]),
        *([] if status != DevReleaseSupportedStatus.undecided.value else ["supported_status_required"]),
    ]
    release_ready = not blockers
    next_actions = [
        *_dev_release_plan_workdir_actions(
            workdir_status=workdir_status,
            candidate=candidate_text,
            probe_ref=supplied_probe_ref,
            supported_status=status,
        ),
        *_dev_release_plan_blocker_actions(
            [blocker for blocker in blockers if not blocker.startswith("workdir_")],
            workdir=resolved_workdir,
            candidate=candidate_text,
            probe_ref=supplied_probe_ref,
            supported_status=status,
        ),
        *_dev_release_plan_evidence_actions(workdir=resolved_workdir, release_probe_ref=release_probe_ref, release_ready=release_ready),
    ]
    payload = {
        "ready": release_ready,
        "status": "ready" if release_ready else "blocked",
        "workdir": str(resolved_workdir),
        "workdir_state": workdir_state,
        "release_plan_summary": {
            "schema_version": DEV_RELEASE_PLAN_SCHEMA_VERSION,
            "candidate": candidate_text,
            "probe_ref": release_probe_ref,
            "probe_ref_source": probe_ref_source,
            "supported_status": status,
            "workdir_state": workdir_status,
            "ready": release_ready,
            "blocker_kinds": blockers,
            "next_action_kinds": [action["kind"] for action in next_actions],
        },
        "next_actions": next_actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="release_plan_summary")


def print_dev_release_plan(payload: dict) -> None:
    summary = payload.get("release_plan_summary") if isinstance(payload.get("release_plan_summary"), dict) else {}
    typer.echo("Loopora release readiness plan")
    typer.echo(f"status: {payload.get('status')}")
    typer.echo(f"workdir: {payload.get('workdir')}")
    typer.echo(f"candidate: {summary.get('candidate') or 'required'}")
    probe_ref = str(summary.get("probe_ref") or "").strip()
    probe_ref_source = str(summary.get("probe_ref_source") or "").strip()
    probe_ref_suffix = f" ({probe_ref_source})" if probe_ref and probe_ref_source else ""
    typer.echo(f"release probe ref: {probe_ref or 'candidate required'}{probe_ref_suffix}")
    typer.echo(f"supported status: {summary.get('supported_status')}")
    typer.echo(f"ready for maintainer release decision: {str(bool(summary.get('ready'))).lower()}")
    blockers = [str(blocker) for blocker in list(summary.get("blocker_kinds") or []) if str(blocker).strip()]
    if blockers:
        typer.echo(f"blockers: {', '.join(blockers)}")
    typer.echo("actions:")
    for action in [item for item in list(payload.get("next_actions") or []) if isinstance(item, dict)]:
        text = _dev_release_plan_action_text(action)
        if text:
            typer.echo(f"- {text}")


def _dev_release_plan_evidence_actions(*, workdir: Path, release_probe_ref: str, release_ready: bool) -> list[dict[str, object]]:
    if not release_ready:
        return []
    probe_ref = str(release_probe_ref or "").strip()
    return [
        {
            "kind": "collect_release_decision_evidence",
            "command": dev_check_recovery_command(
                copyable_dev_check_command("--list --pr-evidence"),
                workdir=workdir,
                always_include_workdir=True,
            ),
        },
        {
            "kind": "run_release_focused_evidence",
            "command": dev_check_recovery_command(
                copyable_dev_check_command("--focused recommended"),
                workdir=workdir,
                always_include_workdir=True,
            ),
        },
        {
            "kind": "run_final_release_pr_evidence",
            "command": dev_check_recovery_command(
                copyable_dev_check_command("--pr-evidence --focused-ran recommended"),
                workdir=workdir,
                always_include_workdir=True,
            ),
        },
        {
            "kind": "run_web_journey_checks_if_web_changed",
            "command": _dev_release_plan_uv_run_command(workdir, "pytest -q tests/checks/journeys"),
            "conditional": True,
        },
        {
            "kind": "run_release_real_probe_suite",
            "command": f"gh workflow run real-provider-probe.yml --ref {shlex.quote(probe_ref)} -f suites=release",
            "workflow": ".github/workflows/real-provider-probe.yml",
            "dispatch": "workflow_dispatch",
            "ref": probe_ref,
            "artifact": ".loopora/real-probes/",
            "opt_in": True,
        },
        {
            "kind": "update_changelog_release_notes",
            "file": "CHANGELOG.md",
            "requires": ["version_or_tag", "release_date", "supported_status", "verification_evidence", "skipped_probes", "residual_risks"],
        },
        {"kind": "review_security_support_scope", "file": "SECURITY.md"},
        {"kind": "verify_package_distribution_boundary", "covered_by": "package_build", "no_license_boundary": True},
    ]


def _dev_release_plan_workdir_actions(*, workdir_status: str, candidate: str, probe_ref: str, supported_status: str) -> list[dict[str, object]]:
    if workdir_status == "ready":
        return []
    return [
        {
            "kind": "choose_release_workdir",
            "option": "--workdir <Loopora checkout>",
            "command_template": _dev_release_plan_rerun_command_template(
                workdir="<Loopora checkout>",
                candidate=candidate,
                probe_ref=probe_ref,
                supported_status=supported_status,
            ),
            "workdir_state": workdir_status,
            "reason": "release evidence commands need an existing Loopora checkout workdir",
        }
    ]


def _dev_release_plan_blocker_actions(
    blockers: list[str],
    *,
    workdir: Path,
    candidate: str,
    probe_ref: str,
    supported_status: str,
) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    if "candidate_required" in blockers:
        actions.append(
            {
                "kind": "choose_release_candidate",
                "option": "--candidate <version-or-tag>",
                "command_template": _dev_release_plan_rerun_command_template(
                    workdir=workdir,
                    candidate="<version-or-tag>",
                    probe_ref=probe_ref,
                    supported_status=supported_status,
                ),
                "reason": "release notes and evidence need the candidate version or tag before maintainer approval",
            }
        )
    if "supported_status_required" in blockers:
        actions.append(
            {
                "kind": "decide_supported_status",
                "option": "--supported-status supported|unsupported",
                "command_template": _dev_release_plan_rerun_command_template(
                    workdir=workdir,
                    candidate=candidate,
                    probe_ref=probe_ref,
                    supported_status="<supported-status>",
                ),
                "choices": ["supported", "unsupported"],
                "reason": "SECURITY.md support status must be explicit before release notes or distribution evidence are final",
            }
        )
    return actions


def _dev_release_plan_rerun_command_template(*, workdir: Path | str, candidate: str, probe_ref: str, supported_status: str) -> str:
    candidate_arg = _dev_release_plan_shell_value(candidate or "<version-or-tag>")
    status_arg = (
        _dev_release_plan_shell_value(supported_status)
        if supported_status and supported_status != DevReleaseSupportedStatus.undecided.value
        else "<supported-status>"
    )
    command = f"uv run loopora dev release-plan --candidate {candidate_arg} --supported-status {status_arg}"
    probe_ref_arg = str(probe_ref or "").strip()
    if probe_ref_arg:
        command = f"{command} --probe-ref {_dev_release_plan_shell_value(probe_ref_arg)}"
    workdir_arg = _dev_release_plan_workdir_arg(workdir, always_include_current=True)
    return f"{command} --workdir {shlex.quote(workdir_arg)}" if workdir_arg else command


def _dev_release_plan_shell_value(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("<") and text.endswith(">"):
        return text
    return shlex.quote(text)


def _dev_release_plan_workdir_arg(workdir: Path | str, *, always_include_current: bool = False) -> str:
    if isinstance(workdir, Path):
        resolved = workdir.resolve(strict=False)
        return str(resolved) if always_include_current or resolved != Path.cwd().resolve() else ""
    return str(workdir or "").strip()


def _dev_release_plan_uv_run_command(workdir: Path, command: str) -> str:
    return f"uv --directory {shlex.quote(str(workdir.resolve()))} run {str(command or '').strip()}"


def _dev_release_plan_action_text(action: dict) -> str:
    kind = str(action.get("kind") or "").strip()
    command = str(action.get("command") or "").strip()
    text = kind
    if kind in {"collect_release_decision_evidence", "run_release_focused_evidence", "run_final_release_pr_evidence"}:
        text = f"{kind}: {command}"
    elif kind in {"run_web_journey_checks_if_web_changed", "run_release_real_probe_suite"}:
        suffix = " (conditional)" if action.get("conditional") else " (opt-in)" if action.get("opt_in") else ""
        text = f"{kind}: {command}{suffix}"
    elif kind in {"choose_release_workdir", "choose_release_candidate", "decide_supported_status"}:
        command_template = str(action.get("command_template") or "").strip()
        suffix = f"; rerun: {command_template}" if command_template else ""
        text = f"{kind}: {action.get('option')} - {action.get('reason')}{suffix}"
    elif kind == "update_changelog_release_notes":
        text = f"{kind}: {action.get('file')} records supported status, evidence, skipped probes, and residual risks"
    elif kind == "review_security_support_scope":
        text = f"{kind}: {action.get('file')}"
    elif kind == "verify_package_distribution_boundary":
        text = f"{kind}: {action.get('covered_by')} keeps package contents and no-license boundary checked"
    return text
