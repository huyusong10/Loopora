from __future__ import annotations

import pytest

from loopora.step_instruction_context import (
    required_step_instruction_context_from_mapping,
    step_instruction_context_from_mapping,
)


def test_step_instruction_context_mapping_prefers_step_instruction_key() -> None:
    preferred = {"source": "step_instruction"}
    old_packet = {"source": "old_packet"}

    assert step_instruction_context_from_mapping(
        {"step_instruction_context": preferred, "context_packet": old_packet}
    ) == preferred


def test_step_instruction_context_mapping_ignores_old_context_packet() -> None:
    old_packet = {"source": "old_packet"}

    assert step_instruction_context_from_mapping({"context_packet": old_packet}) == {}


def test_required_step_instruction_context_mapping_fails_when_no_context_key_exists() -> None:
    with pytest.raises(KeyError):
        required_step_instruction_context_from_mapping({"other": {}})


def test_required_step_instruction_context_mapping_rejects_old_context_packet() -> None:
    old_packet = {"source": "old_packet"}

    with pytest.raises(KeyError):
        required_step_instruction_context_from_mapping({"context_packet": old_packet})
