from __future__ import annotations

import re


_LANGUAGE_AWARE_COMMAND = re.compile(
    r"(?:^|\s)loopora\s+(?:doctor|fit|support|init\s+(?:current|codex|claude|opencode)|"
    r"agent\s+(?:codex|claude|opencode)\s+check)(?:\s|$)"
)


def agent_entry_text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english


def localized_agent_entry_command(command: str, *, language: str) -> str:
    command = str(command or "").strip()
    if language != "zh" or not command or "--language" in command:
        return command
    if not _LANGUAGE_AWARE_COMMAND.search(command):
        return command
    return f"{command} --language zh"


__all__ = ("agent_entry_text", "localized_agent_entry_command")
