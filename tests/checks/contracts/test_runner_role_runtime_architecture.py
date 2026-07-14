from __future__ import annotations

import pytest

from loopora.runner_role_execution_settings import resolve_runner_role_execution_settings
from loopora.service_types import LooporaError

from runner_architecture_test_support import design_contracts_source, loopora_source


def test_runner_role_execution_settings_have_dedicated_boundary() -> None:
    runtime_source = loopora_source("service_runner_step_runtime.py")
    settings_source = loopora_source("runner_role_execution_settings.py")
    contracts_source = design_contracts_source()

    assert "from loopora.runner_role_execution_settings import resolve_runner_role_execution_settings" in runtime_source
    assert "def _resolve_role_execution_settings" in runtime_source
    assert "return resolve_runner_role_execution_settings(run, step, role)" in runtime_source
    for marker in (
        "def resolve_runner_role_execution_settings",
        "strategy_role_uses_execution_snapshot",
        "normalize_loop_compose_execution_options",
    ):
        assert marker in settings_source
    assert "validate_command_args_text" not in settings_source
    assert "normalize_executor_kind" not in settings_source
    assert all(marker not in runtime_source for marker in ("strategy_role_uses_execution_snapshot", "validate_command_args_text"))
    assert "runner_role_execution_settings.py" in contracts_source


def test_runner_role_execution_settings_use_shared_run_execution_normalization_with_step_overrides() -> None:
    settings = resolve_runner_role_execution_settings(
        {
            "executor_kind": "claude-code",
            "executor_mode": "preset",
            "model": "",
            "reasoning_effort": "not-a-real-effort",
        },
        {"model": "step-model", "inherit_session": True, "extra_cli_args": "--verbose"},
        {},
    )

    assert settings == {
        "executor_kind": "claude",
        "executor_mode": "preset",
        "command_cli": "",
        "command_args_text": "",
        "model": "step-model",
        "reasoning_effort": "",
        "step_model": "step-model",
        "inherit_session": True,
        "extra_cli_args_text": "--verbose",
    }


def test_runner_role_execution_settings_use_shared_role_snapshot_normalization() -> None:
    settings = resolve_runner_role_execution_settings(
        {"executor_kind": "codex", "executor_mode": "preset", "model": "run-model"},
        {"model": "step-model"},
        {
            "id": "reviewer",
            "archetype": "custom",
            "executor_kind": "claude-code",
            "executor_mode": "preset",
            "model": "role-model",
            "reasoning_effort": "xhigh",
        },
    )

    assert settings["executor_kind"] == "claude"
    assert settings["model"] == "step-model"
    assert settings["reasoning_effort"] == "max"


def test_runner_role_execution_settings_reject_invalid_role_snapshot_command_template() -> None:
    with pytest.raises(LooporaError) as exc_info:
        resolve_runner_role_execution_settings(
            {"executor_kind": "codex", "executor_mode": "preset"},
            {},
            {
                "id": "custom",
                "archetype": "custom",
                "executor_kind": "custom",
                "executor_mode": "command",
                "command_args_text": "{schema_path}",
            },
        )

    assert str(exc_info.value) == "custom command is missing required placeholders: {prompt}, {output_path}"


def test_service_role_execution_lifecycle_has_dedicated_boundary() -> None:
    role_source = loopora_source("service_role_execution.py")
    lifecycle_source = loopora_source("service_role_execution_lifecycle.py")
    legacy_requests_source = loopora_source("service_legacy_role_requests.py")
    runtime_source = loopora_source("service_runner_step_runtime.py")
    contracts_source = design_contracts_source()

    assert "from loopora.service_role_execution_lifecycle import" in role_source
    assert "from loopora.service_legacy_role_requests import" in role_source
    assert "class ServiceRoleExecutionMixin(ServiceRoleExecutionLifecycleMixin, ServiceLegacyRoleRequestMixin)" in role_source
    assert "from loopora.service_role_execution import RoleExecutionRequest" in runtime_source
    for marker in (
        "class RoleExecutionRequest",
        "def _wait_for_slot",
        "def _pause_between_iterations",
        "def _execute_role",
        "def _ensure_not_stopped",
        "def _set_mode",
    ):
        assert marker in lifecycle_source
        assert marker not in role_source
    for marker in ("def _run_check_planner", "def _run_generator", "def _run_tester", "def _execute_request"):
        assert marker in legacy_requests_source
        assert marker not in role_source
        assert marker not in lifecycle_source
    assert "class IterationRoleRunRequest" in legacy_requests_source
    assert "class IterationRoleRunRequest" not in role_source
    for marker in ("def _resolve_run_checks",):
        assert marker in role_source
        assert marker not in lifecycle_source
        assert marker not in legacy_requests_source
    assert "service_role_execution_lifecycle.py" in contracts_source
    assert "service_legacy_role_requests.py" in contracts_source
