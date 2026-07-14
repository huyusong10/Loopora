from __future__ import annotations

import re


_SERVE_COMMAND = re.compile(r"(?:^|\s)loopora\s+serve(?:\s|$)")


def serve_text(language: str, english: str, chinese: str) -> str:
    return chinese if language == "zh" else english


def localized_serve_command(command: str, *, language: str) -> str:
    command = str(command or "").strip()
    if language != "zh" or not command or "--language" in command:
        return command
    if not _SERVE_COMMAND.search(command):
        return command
    return f"{command} --language zh"


__all__ = ("localized_serve_command", "serve_text")
