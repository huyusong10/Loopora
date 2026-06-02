from __future__ import annotations

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
        "validate_command_args_text",
        "normalize_reasoning_effort",
    ):
        assert marker in settings_source
    assert all(marker not in runtime_source for marker in ("strategy_role_uses_execution_snapshot", "validate_command_args_text"))
    assert "runner_role_execution_settings.py" in contracts_source


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
