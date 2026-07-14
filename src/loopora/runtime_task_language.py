from __future__ import annotations

from collections.abc import Mapping


def runtime_task_language_from_text(value: object) -> str:
    return "zh" if any("\u4e00" <= char <= "\u9fff" for char in str(value or "")) else "en"


def runtime_task_language(compiled_spec: Mapping[str, object]) -> str:
    fragments = [
        compiled_spec.get("goal"),
        compiled_spec.get("constraints"),
        compiled_spec.get("success_surface"),
        compiled_spec.get("fake_done_states"),
        compiled_spec.get("evidence_preferences"),
        compiled_spec.get("residual_risk"),
        compiled_spec.get("checks"),
        compiled_spec.get("role_notes"),
    ]
    return runtime_task_language_from_text(fragments)


def runtime_task_text(language: str, english: str, chinese: str) -> str:
    return chinese if str(language or "").strip().lower() == "zh" else english


__all__ = [
    "runtime_task_language",
    "runtime_task_language_from_text",
    "runtime_task_text",
]
