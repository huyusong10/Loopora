from __future__ import annotations

from collections.abc import Mapping
from typing import Any

STEP_INSTRUCTION_CONTEXT_KEY = "step_instruction_context"


def step_instruction_context_from_mapping(source: object) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        return {}
    value = source.get(STEP_INSTRUCTION_CONTEXT_KEY)
    if isinstance(value, dict):
        return value
    return {}


def required_step_instruction_context_from_mapping(source: object) -> dict[str, Any]:
    if isinstance(source, Mapping) and STEP_INSTRUCTION_CONTEXT_KEY in source:
        return step_instruction_context_from_mapping(source)
    raise KeyError(STEP_INSTRUCTION_CONTEXT_KEY)
