from __future__ import annotations

import re


_LANGUAGE_AWARE_RECOVERY_COMMAND = re.compile(
    r"(?:^|\s)loopora\s+(?:doctor|status|dev\s+reset|recovery\s+(?:create|inspect|restore))(?:\s|$)"
)


def recovery_text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english


def localized_recovery_command(command: str, *, language: str) -> str:
    command = str(command or "").strip()
    if language != "zh" or not command or "--language" in command:
        return command
    if not _LANGUAGE_AWARE_RECOVERY_COMMAND.search(command):
        return command
    return f"{command} --language zh"


__all__ = ("localized_recovery_command", "recovery_text")
