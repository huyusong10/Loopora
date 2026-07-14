from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FocusedCheckGuide:
    id: str
    label: str
    when: str
    command: str
    evidence_type: str
    path_patterns: tuple[str, ...]


__all__ = ("FocusedCheckGuide",)
