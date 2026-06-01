from __future__ import annotations

from loopora.agent_native_submit_hints import agent_native_submit_command

from agent_adapter_test_support import (
    Path,
    _assert_codex_native_surface_summary,
    _assert_loopora_cli_command,
    agent_adapters,
    cli_agent_adapter_commands,
    shlex,
)


def test_cli_agent_recovery_has_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    adapter_commands_source = (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(
        encoding="utf-8"
    )
    native_source = (root / "src" / "loopora" / "cli_agent_native.py").read_text(encoding="utf-8")
    recovery_source = (root / "src" / "loopora" / "cli_agent_recovery.py").read_text(encoding="utf-8")
    runtime_commands_source = (root / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(
        encoding="utf-8"
    )
    output_source = (root / "src" / "loopora" / "cli_agent_context_recovery_output.py").read_text(
        encoding="utf-8"
    )
    results_source = (root / "src" / "loopora" / "cli_agent_recovery_results.py").read_text(encoding="utf-8")
    active_runs_source = (root / "src" / "loopora" / "cli_agent_recovery_active_runs.py").read_text(
        encoding="utf-8"
    )
    choices_source = (root / "src" / "loopora" / "cli_agent_recoverable_context_output.py").read_text(
        encoding="utf-8"
    )
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora import cli_agent_recovery as _agent_recovery" in adapter_commands_source
    assert "from loopora.cli_agent_recovery import" in runtime_commands_source
    assert "from loopora.cli_agent_recovery import" in native_source
    assert "from loopora.cli_agent_recovery_results import" in recovery_source
    assert "from loopora.cli_agent_recovery_active_runs import" in results_source
    for marker in (
        "def _agent_next_recovery_result",
        "def _agent_loop_unready_recovery_result",
    ):
        assert marker in results_source
        assert marker not in recovery_source
        assert marker not in native_source
    for marker in (
        "def _agent_active_run_conflict_recovery_result",
        "def _active_run_recovery_projection",
        "def _attach_agent_next_commands_to_recovery_choices",
    ):
        assert marker in active_runs_source
        assert marker not in results_source
    assert "cli_agent_recoverable_context_output" in output_source
    for marker in (
        "def attach_recoverable_context_summary",
        "def recoverable_context_choice_summary",
        "def print_recoverable_context_choices",
        "def display_recoverable_context_choices",
    ):
        assert marker in choices_source
        assert marker not in output_source
    for marker in (
        "def _print_agent_next_recovery_result",
        "def _print_agent_loop_recovery_result",
    ):
        assert marker in recovery_source
        assert marker not in native_source
    assert "cli_agent_recovery.py" in design_source
    assert "cli_agent_recovery_results.py" in design_source
    assert "cli_agent_recovery_active_runs.py" in design_source
    assert "cli_agent_recoverable_context_output.py" in design_source


def test_cli_agent_adapter_lifecycle_commands_have_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    adapter_commands_source = (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(
        encoding="utf-8"
    )
    runtime_commands_source = (root / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(
        encoding="utf-8"
    )
    lifecycle_source = (root / "src" / "loopora" / "cli_agent_adapter_lifecycle_commands.py").read_text(
        encoding="utf-8"
    )
    options_source = (root / "src" / "loopora" / "cli_agent_command_options.py").read_text(encoding="utf-8")
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora import cli_agent_adapter_lifecycle_commands as _agent_adapter_lifecycle_commands" in adapter_commands_source
    assert "_agent_adapter_lifecycle_commands.register_agent_adapter_lifecycle_commands" in adapter_commands_source
    assert "from loopora import cli_agent_runtime_commands as _agent_runtime_commands" in adapter_commands_source
    assert "_agent_runtime_commands.register_agent_runtime_commands" in adapter_commands_source
    assert "_agent_adapter_lifecycle_commands.register_agent_check_command" in runtime_commands_source
    assert "from loopora.cli_agent_command_options import" not in adapter_commands_source
    assert "from loopora.cli_agent_command_options import" in runtime_commands_source
    assert "from loopora.cli_agent_command_options import" in lifecycle_source
    for marker in (
        "def _register_init_commands",
        "def _register_uninstall_commands",
        "def _install_adapter",
        "def _uninstall_adapter",
        "def register_agent_check_command",
    ):
        assert marker in lifecycle_source
        assert marker not in adapter_commands_source
    for marker in (
        "AdapterWorkdirOption = Annotated",
        "ContextIdOption = Annotated",
        "ResultFileOption = Annotated",
        "SourceOptionIdOption = Annotated",
    ):
        assert marker in options_source
        assert marker not in adapter_commands_source
        assert marker not in runtime_commands_source
        assert marker not in lifecycle_source
    assert "cli_agent_adapter_lifecycle_commands.py" in design_source
    assert "cli_agent_runtime_commands.py" in design_source
    assert "cli_agent_command_options.py" in design_source


def test_cli_agent_runtime_actions_have_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    adapter_commands_source = (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(
        encoding="utf-8"
    )
    runtime_commands_source = (root / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(
        encoding="utf-8"
    )
    actions_source = (root / "src" / "loopora" / "cli_agent_runtime_actions.py").read_text(encoding="utf-8")
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora import cli_agent_runtime_actions as _agent_runtime_actions" in adapter_commands_source
    assert "from loopora.cli_agent_runtime_actions import" in runtime_commands_source
    for marker in (
        "def claim_agent_next_from_cli",
        "def handle_agent_submit_error",
        "def handle_agent_plan_error",
        "def start_agent_loop_from_cli",
    ):
        assert marker in actions_source
        assert marker not in adapter_commands_source
        assert marker not in runtime_commands_source
    assert "cli_agent_runtime_actions.py" in design_source
    assert "cli_agent_runtime_commands.py" in design_source


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


def test_agent_native_generated_cli_commands_preserve_loopora_home(monkeypatch, tmp_path: Path) -> None:
    home = tmp_path / "loopora home"
    workdir = tmp_path / "project with spaces"
    result_file = workdir / ".loopora" / "agent_outbox" / "codex" / "run_agent__iter000__step00__builder_step.result.json"
    monkeypatch.setenv("LOOPORA_HOME", str(home))
    expected_prefix = f"LOOPORA_HOME={shlex.quote(str(home))} LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill "

    run_command = agent_adapters.agent_loop_json_command("codex", workdir, entry_source="codex_project_skill")
    submit_command = agent_native_submit_command(
        adapter="codex",
        run_id="run_agent",
        step_id="builder_step",
        entry_source="codex_project_skill",
        result_file=str(result_file),
    )
    next_command = cli_agent_adapter_commands._agent_next_command_hint(
        adapter="codex",
        workdir=workdir,
        context_id="",
        run_id="run_agent",
        entry_source="codex_project_skill",
    )
    repair_command = cli_agent_adapter_commands._agent_plan_cli_command(
        adapter="codex",
        workdir=str(workdir),
        message="Repair the focused deletion-flow Loop.",
        entry_source="codex_project_skill",
        bundle_file=str(workdir / "candidate.yml"),
    )
    next_commands = agent_adapters._adapter_install_next_commands("codex", workdir)
    check_recovery = agent_adapters._adapter_check_recovery(
        "codex",
        workdir,
        status={"status": "not_installed"},
        check_status="fail",
    )

    assert run_command.startswith(expected_prefix)
    assert submit_command.startswith(expected_prefix)
    assert next_command.startswith(expected_prefix)
    assert repair_command.startswith(expected_prefix)
    assert f"--workdir {shlex.quote(str(workdir))}" in run_command
    assert f"--result-file {shlex.quote(str(result_file))}" in submit_command
    assert f"--workdir {shlex.quote(str(workdir))}" in next_command
    assert f"--bundle-file {shlex.quote(str(workdir / 'candidate.yml'))}" in repair_command
    _assert_loopora_cli_command(
        next_commands["check"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))} --check",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        next_commands["agent_check"],
        f"loopora agent codex check --workdir {shlex.quote(str(workdir))}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        check_recovery["install_command"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        check_recovery["check_command"],
        f"loopora init codex --workdir {shlex.quote(str(workdir))} --check",
        loopora_home=home,
    )


def test_agent_next_summary_reports_dispatch_recovery_commands_when_target_config_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "loopora home"
    workdir = tmp_path / "project"
    monkeypatch.setenv("LOOPORA_HOME", str(home))

    summary = cli_agent_adapter_commands._agent_next_summary(
        {
            "adapter": "codex",
            "workdir": str(workdir),
            "run": {"id": "run_next", "status": "awaiting_agent", "workdir": str(workdir)},
            "next_step": {
                "adapter": "codex",
                "step_id": "contract_inspection_step",
                "role": {"name": "Contract Inspector"},
                "role_dispatch": {
                    "target_agent": "loopora-inspector",
                    "target_agent_config_absolute_path": str(workdir / ".codex" / "agents" / "loopora-inspector.toml"),
                    "target_agent_config_exists": False,
                },
            },
        }
    )

    next_step = summary["next_step"]
    _assert_codex_native_surface_summary(summary)
    assert "dispatch_next" not in next_step
    assert next_step["target_agent_config_exists"] is False
    dispatch_unavailable = next_step["dispatch_unavailable"]
    assert dispatch_unavailable["reason"] == "target_agent_config_missing"
    assert dispatch_unavailable["target_agent"] == "loopora-inspector"
    _assert_loopora_cli_command(
        dispatch_unavailable["check_command"],
        f"loopora agent codex check --workdir {workdir}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        dispatch_unavailable["repair_command"],
        f"loopora init codex --workdir {workdir}",
        loopora_home=home,
    )
    assert "do not submit inline role work" in dispatch_unavailable["next"]
