from __future__ import annotations

from loopora.cli_first_task_handoff import FIRST_TASK_ORIENTATION_EXAMPLE_ZH
from loopora.cli_recovery_language import localized_recovery_command
from loopora.cli_serve_language import localized_serve_command

def doctor_text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english


def doctor_localized_action_command(action: dict, *, language: str) -> str:
    command = str(action.get("command") or "").strip()
    kind = str(action.get("kind") or "").strip()
    command = localized_recovery_command(command, language=language)
    command = localized_serve_command(command, language=language)
    if language != "zh" or kind not in {"check_fit_first", "confirm_readiness", "support"}:
        return command
    if not command or "--language" in command:
        return command
    return f"{command} --language zh"


DOCTOR_FIRST_TASK_EXAMPLE_ZH = FIRST_TASK_ORIENTATION_EXAMPLE_ZH


__all__ = ("DOCTOR_FIRST_TASK_EXAMPLE_ZH", "doctor_localized_action_command", "doctor_text")
