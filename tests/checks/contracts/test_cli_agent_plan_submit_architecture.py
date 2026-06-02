from __future__ import annotations

from pathlib import Path


def test_cli_agent_submit_repair_results_have_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    repair_source = (root / "src" / "loopora" / "cli_agent_submit_repair.py").read_text(encoding="utf-8")
    results_source = (root / "src" / "loopora" / "cli_agent_submit_repair_results.py").read_text(
        encoding="utf-8"
    )
    guidance_source = (root / "src" / "loopora" / "cli_agent_submit_repair_guidance.py").read_text(
        encoding="utf-8"
    )
    auto_repair_source = (root / "src" / "loopora" / "cli_agent_submit_auto_repair.py").read_text(
        encoding="utf-8"
    )
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_submit_repair_results import" in repair_source
    assert "from loopora.cli_agent_submit_repair_results import _active_agent_native_step_view" in auto_repair_source
    assert "from loopora.cli_agent_submit_repair_guidance import" in results_source
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


def test_cli_agent_plan_results_have_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    output_source = (root / "src" / "loopora" / "cli_agent_plan_output.py").read_text(encoding="utf-8")
    guidance_output_source = (root / "src" / "loopora" / "cli_agent_plan_guidance_output.py").read_text(
        encoding="utf-8"
    )
    results_source = (root / "src" / "loopora" / "cli_agent_plan_results.py").read_text(encoding="utf-8")
    plan_recovery_source = (root / "src" / "loopora" / "cli_agent_plan_recovery_results.py").read_text(
        encoding="utf-8"
    )
    recovery_source = (root / "src" / "loopora" / "cli_agent_recovery.py").read_text(encoding="utf-8")
    recovery_results_source = (root / "src" / "loopora" / "cli_agent_recovery_results.py").read_text(
        encoding="utf-8"
    )
    adapter_commands_source = (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(
        encoding="utf-8"
    )
    runtime_commands_source = (root / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(
        encoding="utf-8"
    )
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_plan_results import" in output_source
    assert "from loopora.cli_agent_plan_results import" in recovery_source
    assert "from loopora.cli_agent_plan_recovery_results import" in output_source
    assert "from loopora.cli_agent_plan_recovery_results import" in recovery_results_source
    assert "from loopora import cli_agent_plan_output as _agent_plan_output" in adapter_commands_source
    assert "from loopora.cli_agent_plan_output import _print_agent_gen_result" in runtime_commands_source
    assert "from loopora.cli_agent_plan_output import _print_agent_gen_result" not in adapter_commands_source
    for marker in (
        "def _agent_gen_json_payload",
        "def _agent_plan_summary",
    ):
        assert marker in results_source
        assert marker not in output_source
        assert marker not in plan_recovery_source
    for marker in (
        "def _attach_agent_gen_recovery_fields",
        "def _attach_agent_web_review_recovery_fields",
        "def _agent_repair_cli_command",
    ):
        assert marker in plan_recovery_source
        assert marker not in output_source
        assert marker not in results_source
    assert "def _print_agent_gen_result" in output_source
    assert "from loopora.cli_agent_plan_guidance_output import" in output_source
    for marker in ("def _print_agent_repair_guidance", "def _print_agent_web_review_guidance"):
        assert marker in guidance_output_source
        assert marker not in output_source
        assert marker not in results_source
    assert "cli_agent_plan_results.py" in design_source
    assert "cli_agent_plan_recovery_results.py" in design_source
    assert "cli_agent_plan_guidance_output.py" in design_source
