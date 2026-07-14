from __future__ import annotations

import typer

from loopora.cli_diagnose_doctor_app_output import print_doctor_app_state
from loopora.cli_diagnose_doctor_entries_output import print_doctor_entries
from loopora.cli_diagnose_doctor_next_steps_output import print_doctor_next_steps
from loopora.cli_diagnose_doctor_summary_output import doctor_workdir_usable
from loopora.cli_diagnose_doctor_summary_output import print_doctor_package
from loopora.cli_diagnose_doctor_summary_output import print_doctor_readiness_summary
from loopora.cli_diagnose_doctor_summary_output import print_doctor_workdir_state
from loopora.cli_diagnose_doctor_web_output import print_doctor_web
from loopora.cli_diagnose_doctor_language import DOCTOR_FIRST_TASK_EXAMPLE_ZH, doctor_text
from loopora.cli_first_task_handoff import echo_first_task_handoff


def print_doctor_report(report: dict, *, strict: bool = False, language: str = "en") -> None:
    ready = report.get("agent_entry_ready", report.get("ready")) is True
    status = str(report.get("status") or "unknown")
    if language == "zh":
        typer.echo(f"Loopora Doctor：{_doctor_status_zh(status)}（{status}）")
    else:
        typer.echo(f"Loopora doctor: {status}")
    typer.echo(
        doctor_text(
            language,
            f"same-Agent project entry ready: {'yes' if ready else 'no'}",
            f"同一 Agent 项目入口就绪：{'是' if ready else '否'}",
        )
    )
    if strict:
        strict_ready = report.get("strict_ready") is True
        typer.echo(doctor_text(language, f"strict readiness: {'yes' if strict_ready else 'no'}", f"严格就绪：{'是' if strict_ready else '否'}"))
    print_doctor_readiness_summary(report, language=language)
    typer.echo(doctor_text(language, f"project directory: {report.get('workdir')}", f"项目目录：{report.get('workdir')}"))
    print_doctor_workdir_state(report, language=language)
    print_doctor_package(report, language=language)
    if doctor_workdir_usable(report):
        print_doctor_app_state(report, language=language)
        print_doctor_web(report, language=language)
    print_doctor_entries(report, language=language)
    print_doctor_next_steps(report, language=language)
    echo_first_task_handoff(
        report,
        language=language,
        example=DOCTOR_FIRST_TASK_EXAMPLE_ZH if language == "zh" else None,
    )


def _doctor_status_zh(status: str) -> str:
    return {
        "ready": "已就绪",
        "ready_with_warnings": "已就绪但有警告",
        "not_ready": "未就绪",
        "target_required": "需要目标项目",
    }.get(status, "状态未知")
