from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from loopora.cli_agent_adapter_lifecycle_commands import AdapterWorkdirOption
from loopora.cli_common import get_service
from loopora.cli_shared import JsonOutputOption, echo_json, handle_error
from loopora.diagnose_doctor import build_doctor_report, doctor_json_payload
from loopora.service import LooporaError

from loopora.event_redaction_audit_files import audit_alignment_event_files, audit_timeline_files

from loopora.event_redaction_audit_files import combine_event_redaction_reports

from loopora.event_redaction import redact_alignment_event_payload, redact_run_event_payload

from loopora.event_redaction_audit_files import event_redaction_sample, redaction_changed

def audit_db_events(repository, *, fix: bool) -> dict:
    scanned = 0
    suspect = 0
    fixed = 0
    samples = []
    unfixable = []
    for event in repository.list_run_events_for_redaction_audit():
        scanned += 1
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        redacted = redact_run_event_payload(str(event.get("event_type") or ""), payload)
        if not redaction_changed(payload, redacted):
            continue
        suspect += 1
        samples.append(event_redaction_sample("db", event, redacted))
        if fix:
            if repository.update_run_event_payload_for_redaction(int(event["id"]), redacted):
                fixed += 1
            else:
                unfixable.append({"source": "db", "event_id": event.get("id"), "reason": "update_failed"})
    return {
        "scanned": scanned,
        "suspect": suspect,
        "fixed": fixed,
        "samples": samples[:20],
        "unfixable": unfixable,
    }

def audit_alignment_db_events(repository, *, fix: bool) -> dict:
    scanned = 0
    suspect = 0
    fixed = 0
    samples = []
    unfixable = []
    if not hasattr(repository, "list_alignment_events_for_redaction_audit"):
        return {"scanned": 0, "suspect": 0, "fixed": 0, "samples": [], "unfixable": []}
    for event in repository.list_alignment_events_for_redaction_audit():
        scanned += 1
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        redacted = redact_alignment_event_payload(str(event.get("event_type") or ""), payload)
        if not redaction_changed(payload, redacted):
            continue
        suspect += 1
        samples.append(event_redaction_sample("alignment_db", event, redacted))
        if fix:
            if repository.update_alignment_event_payload_for_redaction(int(event["id"]), redacted):
                fixed += 1
            else:
                unfixable.append({"source": "alignment_db", "event_id": event.get("id"), "reason": "update_failed"})
    return {
        "scanned": scanned,
        "suspect": suspect,
        "fixed": fixed,
        "samples": samples[:20],
        "unfixable": unfixable,
    }

def audit_event_redaction(repository, *, fix: bool = False) -> dict:
    return combine_event_redaction_reports(
        fix=fix,
        db_events=audit_db_events(repository, fix=fix),
        timeline_files=audit_timeline_files(repository, fix=fix),
        alignment_db_events=audit_alignment_db_events(repository, fix=fix),
        alignment_event_files=audit_alignment_event_files(repository, fix=fix),
    )

def audit_run_event_redaction(repository, *, fix: bool = False) -> dict:
    return audit_event_redaction(repository, fix=fix)

FixOption = Annotated[
    bool,
    typer.Option(
        "--fix",
        help="Rewrite DB and local event files that current redaction rules can safely repair.",
    ),
]


def register_diagnose_commands(app: typer.Typer) -> None:
    @app.command("doctor")
    def diagnose_doctor(
        workdir: AdapterWorkdirOption = Path(),
        *,
        json_output: JsonOutputOption = False,
    ) -> None:
        """Report local first-use readiness without installing or repairing files."""
        run_doctor_command(workdir=workdir, json_output=json_output)

    @app.command("event-redaction")
    def diagnose_event_redaction(
        *,
        fix: FixOption = False,
    ) -> None:
        service = get_service()
        report = audit_event_redaction(service.repository, fix=fix)
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))


def run_doctor_command(*, workdir: Path, json_output: bool) -> None:
    try:
        report = build_doctor_report(workdir=workdir)
    except LooporaError as exc:
        handle_error(exc, json_output=json_output)
        return
    if json_output:
        echo_json(doctor_json_payload(report))
    else:
        _print_doctor_report(report)
    if not report.get("ready"):
        raise typer.Exit(code=1)


def _print_doctor_report(report: dict) -> None:
    ready = report.get("ready") is True
    status = str(report.get("status") or "unknown")
    typer.echo(f"Loopora doctor: {status}")
    typer.echo(f"ready: {'yes' if ready else 'no'}")
    typer.echo(f"workdir: {report.get('workdir')}")
    package = report.get("package") if isinstance(report.get("package"), dict) else {}
    if package:
        typer.echo(f"package: loopora {package.get('version')} (Python {package.get('python')})")
    web = report.get("web") if isinstance(report.get("web"), dict) else {}
    if web:
        token_note = "loopback local default" if web.get("loopback") else "non-loopback requires token or explicit unsafe opt-in"
        typer.echo(f"web: {web.get('origin')} ({token_note})")
        typer.echo(f"web_start: {web.get('start_command')}")
    entries = [entry for entry in list(report.get("agent_entries") or []) if isinstance(entry, dict)]
    if entries:
        typer.echo("agent entries:")
        for entry in entries:
            label = str(entry.get("label") or entry.get("adapter") or "Agent")
            adapter = str(entry.get("adapter") or "")
            check_status = str(entry.get("check_status") or "fail")
            install_state = str(entry.get("install_state") or "unknown")
            next_action = str(entry.get("next_action") or "")
            typer.echo(f"- {label} ({adapter}): {check_status}; install_state={install_state}; next_action={next_action}")
            summary = str(entry.get("summary") or "").strip()
            if summary:
                typer.echo(f"  summary: {summary}")
            commands = entry.get("commands") if isinstance(entry.get("commands"), dict) else {}
            command_key = "install_check" if entry.get("ready") else "install"
            command = str(commands.get(command_key) or commands.get("agent_check") or "").strip()
            if command:
                typer.echo(f"  command: {command}")
    next_steps = [str(item).strip() for item in list(report.get("next_steps") or []) if str(item).strip()]
    if next_steps:
        typer.echo("next:")
        for step in next_steps:
            typer.echo(f"- {step}")
