from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _loopora_source(filename: str) -> str:
    return (ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")


def _design_contracts_source() -> str:
    return (ROOT / "design" / "contracts.md").read_text(encoding="utf-8")


def test_cli_agent_submit_repair_results_have_dedicated_boundary() -> None:
    repair_source = _loopora_source("cli_agent_submit_repair.py")
    results_source = _loopora_source("cli_agent_submit_repair_results.py")
    guidance_source = _loopora_source("cli_agent_submit_repair_guidance.py")
    result_files_source = _loopora_source("cli_agent_result_files.py")
    runtime_support_source = _loopora_source("cli_agent_runtime_support.py")
    auto_repair_source = _loopora_source("cli_agent_submit_auto_repair.py")
    design_source = _design_contracts_source()

    assert "from loopora.cli_agent_submit_repair_results import" in repair_source
    assert "from loopora.cli_agent_submit_repair_results import _active_agent_native_step_view" in auto_repair_source
    assert "from loopora.cli_agent_submit_repair_guidance import" in results_source
    assert "from loopora.cli_agent_result_files import read_result_file_object" in runtime_support_source
    assert "from loopora.cli_agent_result_files import read_result_file_object" in auto_repair_source
    assert "def read_result_file_object" in result_files_source
    for marker in (
        "def _agent_submit_repair_result",
        "def _active_agent_native_step_view",
        "def _agent_submit_repair_focus",
    ):
        assert marker in results_source
        assert marker not in repair_source
    for marker in (
        "def _agent_submit_next_repair_step",
        "def _agent_submit_result_file_dispatch_summary",
        "def _agent_submit_error_is_repairable",
    ):
        assert marker in guidance_source
        assert marker not in results_source
    for marker in (
        "def _print_agent_submit_repair_guidance",
        "def _agent_submit_repair_json_payload",
        "def _agent_submit_repair_summary",
    ):
        assert marker in repair_source
        assert marker not in results_source
    assert "cli_agent_submit_repair_results.py" in design_source
    assert "cli_agent_submit_repair_guidance.py" in design_source
    assert "cli_agent_result_files.py" in design_source


def test_cli_agent_plan_results_have_dedicated_boundary() -> None:
    output_source = _loopora_source("cli_agent_plan_output.py")
    guidance_output_source = _loopora_source("cli_agent_plan_guidance_output.py")
    results_source = _loopora_source("cli_agent_plan_results.py")
    plan_recovery_source = _loopora_source("cli_agent_plan_recovery_results.py")
    recovery_source = _loopora_source("cli_agent_recovery.py")
    recovery_results_source = _loopora_source("cli_agent_recovery_results.py")
    adapter_commands_source = _loopora_source("cli_agent_adapter_commands.py")
    plan_command_source = _loopora_source("cli_agent_plan_command.py")
    design_source = _design_contracts_source()

    assert "from loopora.cli_agent_plan_results import" in output_source
    assert "from loopora.cli_agent_plan_results import" in recovery_source
    assert "from loopora.cli_agent_plan_recovery_results import" in output_source
    assert "from loopora.cli_agent_plan_recovery_results import" in recovery_results_source
    assert "from loopora import cli_agent_plan_output as _agent_plan_output" in adapter_commands_source
    assert "from loopora.cli_agent_plan_output import _print_agent_gen_result" in plan_command_source
    assert "from loopora.cli_agent_plan_output import _print_agent_gen_result" not in adapter_commands_source
    for marker in (
        "def _agent_gen_json_payload",
        "def _agent_plan_summary",
    ):
        assert marker in results_source
        assert marker not in output_source
        assert marker not in plan_recovery_source
    assert "from loopora.cli_agent_plan_recovery_state import" in plan_recovery_source
    assert "from loopora.cli_agent_plan_recovery_repair import" in plan_recovery_source
    assert "from loopora.cli_agent_plan_recovery_web_review import" in plan_recovery_source
    assert "def _print_agent_gen_result" in output_source
    assert "from loopora.cli_agent_plan_guidance_output import" in output_source
    for marker in ("def _print_agent_repair_guidance", "def _print_agent_web_review_guidance"):
        assert marker in guidance_output_source
        assert marker not in output_source
        assert marker not in results_source
    assert "cli_agent_plan_results.py" in design_source
    assert "cli_agent_plan_recovery_results.py" in design_source
    assert "cli_agent_plan_recovery_*.py" in design_source
    assert "cli_agent_plan_guidance_output.py" in design_source


def test_cli_agent_plan_recovery_results_facade_has_dedicated_body_modules() -> None:
    output_source = _loopora_source("cli_agent_plan_output.py")
    results_source = _loopora_source("cli_agent_plan_results.py")
    plan_recovery_source = _loopora_source("cli_agent_plan_recovery_results.py")
    plan_recovery_state_source = _loopora_source("cli_agent_plan_recovery_state.py")
    plan_recovery_common_source = _loopora_source("cli_agent_plan_recovery_common.py")
    plan_recovery_repair_source = _loopora_source("cli_agent_plan_recovery_repair.py")
    plan_recovery_web_review_source = _loopora_source("cli_agent_plan_recovery_web_review.py")
    plan_recovery_assets_source = _loopora_source("cli_agent_plan_recovery_assets.py")

    for marker in (
        "def _attach_agent_gen_recovery_fields",
        "def _attach_agent_ready_run_handoff_fields",
    ):
        assert marker in plan_recovery_state_source
        assert marker not in plan_recovery_source
        assert marker not in output_source
        assert marker not in results_source
    for marker in (
        "def _agent_repair_cli_command",
        "def _agent_entry_return_run_command",
        "def _agent_task_message_from_session",
    ):
        assert marker in plan_recovery_common_source
        assert marker not in plan_recovery_source
        assert marker not in output_source
        assert marker not in results_source
    for marker in (
        "def _attach_agent_candidate_repair_fields",
        "def _agent_plan_repair_action",
        "REPAIR_CLI_COMMAND_POLICY",
    ):
        assert marker in plan_recovery_repair_source
        assert marker not in plan_recovery_state_source
        assert marker not in output_source
        assert marker not in results_source
    for marker in (
        "def _attach_agent_web_review_recovery_fields",
        "def _agent_web_review_focus",
        "NEXT_PLAN_CLI_COMMAND_POLICY",
    ):
        assert marker in plan_recovery_web_review_source
        assert marker not in plan_recovery_state_source
        assert marker not in output_source
        assert marker not in results_source
    assert "def _agent_native_recovery_asset" in plan_recovery_assets_source
    assert "load_system_prompt_asset" in plan_recovery_assets_source
    assert "load_system_prompt_asset" not in plan_recovery_source
