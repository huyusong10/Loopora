from __future__ import annotations

import typer

from loopora.cli_agent_adapter_language import localized_agent_entry_command
from loopora.cli_diagnose_doctor_language import doctor_text
from loopora.diagnose_doctor_projection import doctor_action_step


def print_doctor_next_steps(report: dict, *, language: str = "en") -> None:
    actions = doctor_action_items(report)
    if any(doctor_action_step(item, language=language) for item in actions):
        typer.echo(doctor_text(language, "next:", "下一步："))
        for action in actions:
            step = doctor_action_step(action, language=language)
            if not step:
                continue
            typer.echo(f"- {step}")
            for choice in _doctor_action_adapter_choices(action, language=language):
                typer.echo(f"  - {choice['label']}: {choice['command']}")
        return
    next_steps = [str(item).strip() for item in list(report.get("next_steps") or []) if str(item).strip()]
    if next_steps:
        typer.echo(doctor_text(language, "next:", "下一步："))
        for step in next_steps:
            typer.echo(f"- {step}")


def doctor_action_items(report: dict) -> list[dict]:
    return [item for item in list(report.get("next_action_items") or []) if isinstance(item, dict)]


def _doctor_action_adapter_choices(action: dict, *, language: str) -> list[dict[str, str]]:
    choices = []
    for choice in list(action.get("adapter_choices") or []):
        if not isinstance(choice, dict):
            continue
        label = str(choice.get("label") or choice.get("adapter") or "").strip()
        command = str(choice.get("command") or "").strip()
        if label and command:
            command = localized_agent_entry_command(command, language=language)
            choices.append({"label": label, "command": command})
    return choices
