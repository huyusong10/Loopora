from __future__ import annotations

from collections.abc import Mapping
from typing import Any

STEP_INSTRUCTION_CONTEXT_KEY = "step_instruction_context"
LEGACY_CONTEXT_PACKET_KEY = "context_packet"


def step_instruction_context_from_mapping(source: object) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        return {}
    value = source.get(STEP_INSTRUCTION_CONTEXT_KEY)
    if isinstance(value, dict):
        return value
    legacy_value = source.get(LEGACY_CONTEXT_PACKET_KEY)
    return legacy_value if isinstance(legacy_value, dict) else {}


def required_step_instruction_context_from_mapping(source: object) -> dict[str, Any]:
    if isinstance(source, Mapping) and (
        STEP_INSTRUCTION_CONTEXT_KEY in source or LEGACY_CONTEXT_PACKET_KEY in source
    ):
        return step_instruction_context_from_mapping(source)
    raise KeyError(STEP_INSTRUCTION_CONTEXT_KEY)


def step_instruction_context_legacy_fields(step_instruction_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        STEP_INSTRUCTION_CONTEXT_KEY: step_instruction_context,
        LEGACY_CONTEXT_PACKET_KEY: step_instruction_context,
    }
