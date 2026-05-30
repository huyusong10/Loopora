from __future__ import annotations

import pytest

from loopora.step_instruction_context import (
    required_step_instruction_context_from_mapping,
    step_instruction_context_from_mapping,
    step_instruction_context_legacy_fields,
)


def test_step_instruction_context_mapping_prefers_step_instruction_key() -> None:
    preferred = {"source": "step_instruction"}
    legacy = {"source": "legacy_context_packet"}

    assert step_instruction_context_from_mapping(
        {"step_instruction_context": preferred, "context_packet": legacy}
    ) == preferred


def test_step_instruction_context_mapping_keeps_legacy_context_packet_fallback() -> None:
    legacy = {"source": "legacy_context_packet"}

    assert step_instruction_context_from_mapping({"context_packet": legacy}) == legacy


def test_required_step_instruction_context_mapping_fails_when_no_context_key_exists() -> None:
    with pytest.raises(KeyError):
        required_step_instruction_context_from_mapping({"other": {}})


def test_step_instruction_context_legacy_fields_write_new_key_and_legacy_mirror() -> None:
    step_context = {"iteration": {"iter_index": 1}}

    assert step_instruction_context_legacy_fields(step_context) == {
        "step_instruction_context": step_context,
        "context_packet": step_context,
    }
