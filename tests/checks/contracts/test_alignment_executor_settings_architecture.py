from __future__ import annotations

import pytest

from loopora.service_alignment_executor_settings import AlignmentExecutorSettingsRequest, normalize_alignment_executor_settings
from loopora.service_types import LooporaError

from service_architecture_test_support import design_contracts_source, loopora_source


def test_alignment_executor_settings_have_dedicated_boundary() -> None:
    requests_source = loopora_source("service_alignment_requests.py")
    settings_source = loopora_source("service_alignment_executor_settings.py")
    session_creation_source = loopora_source("service_alignment_session_creation.py")
    contracts_source = design_contracts_source()

    assert "from loopora.service_alignment_executor_settings import" in requests_source
    assert "from loopora.service_alignment_executor_settings import normalize_alignment_executor_settings" in session_creation_source
    for marker in (
        "class AlignmentExecutorSettingsRequest",
        "def default_alignment_executor_settings",
        "def alignment_executor_settings_from_raw",
        "def normalize_alignment_executor_settings",
        "normalize_loop_compose_execution_options",
    ):
        assert marker in settings_source
        assert marker not in requests_source
    assert "validate_command_args_text" not in settings_source
    assert "normalize_executor_kind" not in settings_source
    assert "service_alignment_executor_settings.py" in contracts_source


def test_alignment_executor_settings_use_shared_execution_normalization_for_command_only_executor() -> None:
    settings = normalize_alignment_executor_settings(
        AlignmentExecutorSettingsRequest(
            executor_kind="custom",
            executor_mode="preset",
            command_cli="loopora-runner",
            command_args_text="{prompt}\n--output\n{output_path}",
            model="",
            reasoning_effort="",
        )
    )

    assert settings == {
        "executor_kind": "custom",
        "executor_mode": "command",
        "command_cli": "loopora-runner",
        "command_args_text": "{prompt}\n--output\n{output_path}",
        "model": "",
        "reasoning_effort": "",
    }


def test_alignment_executor_settings_reject_invalid_command_template_with_field_error() -> None:
    with pytest.raises(LooporaError) as exc_info:
        normalize_alignment_executor_settings(
            AlignmentExecutorSettingsRequest(
                executor_kind="custom",
                executor_mode="preset",
                command_cli="loopora-runner",
                command_args_text="{schema_path}",
                model="",
                reasoning_effort="",
            )
        )

    assert str(exc_info.value) == "invalid command_args_text: custom command is missing required placeholders: {prompt}, {output_path}"
