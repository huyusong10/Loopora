from __future__ import annotations

# Merged from test_cli_agent_adapter_output_architecture.py
from loopora.cli_agent_adapter_output import adapter_label

from cli_agent_adapter_output_test_support import design_contracts_source, loopora_source


def test_adapter_output_reuses_shared_adapter_labels() -> None:
    output_source = loopora_source("cli_agent_adapter_output.py")
    design_source = design_contracts_source()

    assert adapter_label("claude") == "Claude Code"
    assert adapter_label("") == "Agent"
    assert "from loopora.agent_adapter_check_utils import adapter_label as _adapter_label" in output_source
    assert '"claude": "Claude Code"' not in output_source
    assert "agent_adapter_check_utils.py" in design_source


def test_adapter_check_output_has_dedicated_boundary() -> None:
    output_source = loopora_source("cli_agent_adapter_output.py")
    check_output_source = loopora_source("cli_agent_adapter_check_output.py")
    design_source = design_contracts_source()

    assert "from loopora import cli_agent_adapter_check_output as _adapter_check_output" in output_source
    for marker in (
        "def adapter_check_json_payload",
        "def adapter_check_summary",
        "def print_adapter_check_recovery",
    ):
        assert marker in check_output_source
        assert marker not in output_source
    assert "agent_v3_envelope(" in check_output_source
    assert "agent_v3_envelope(" not in output_source
    assert "copyable_loopora_command" in check_output_source
    assert "prefix_loopora_command" not in check_output_source
    assert "cli_agent_adapter_check_output.py" in design_source


def test_adapter_install_conflict_output_has_dedicated_boundary() -> None:
    output_source = loopora_source("cli_agent_adapter_output.py")
    conflict_output_source = loopora_source("cli_agent_adapter_conflict_output.py")
    design_source = design_contracts_source()

    assert "from loopora import cli_agent_adapter_conflict_output as _adapter_conflict_output" in output_source
    assert "def handle_adapter_install_conflict" in conflict_output_source
    assert "def adapter_conflict_paths" in conflict_output_source
    assert "def handle_adapter_install_conflict" not in output_source
    assert "def _adapter_conflict_paths" not in output_source
    assert "cli_agent_adapter_conflict_output.py" in design_source


# Merged from test_cli_agent_adapter_output_surface.py
from loopora.cli_agent_adapter_output import print_adapter_mutation_result

from cli_agent_adapter_output_test_support import (
    codex_installed_mutation_result,
)


def test_adapter_output_keeps_first_use_steps_concise_while_json_keeps_surface_details(tmp_path, capsys) -> None:
    print_adapter_mutation_result(
        codex_installed_mutation_result(tmp_path),
        action="installed",
        json_output=False,
    )

    output = capsys.readouterr().out

    assert "Codex Loopora entry is installed" in output
    assert "target project:" in output
    assert "first task message handoff:" in output
    assert "completed fit review:" in output
    assert "copyable /loopora-plan handoff as one Agent message" in output
    assert "generic orientation example (not a completed review):" in output
    assert output.index("completed fit review:") < output.index("generic orientation example")
    assert "next:" in output
    assert "web:" in output
    assert f"loopora serve --open --workdir {tmp_path} --host 127.0.0.1 --port 8742" in output
    assert "diagnostics:" in output
    assert "installed files:" in output
    assert "managed files current" in output
    assert "details: rerun with --json for managed file hashes and the Agent surface contract." in output
    assert "agent surface:" not in output
    assert "managed files:" not in output
    assert "{label}" not in output


def test_adapter_uninstall_output_summarizes_cleanup_and_kept_files(tmp_path, capsys) -> None:
    print_adapter_mutation_result(
        {
            "adapter": "codex",
            "label": "Codex",
            "workdir": str(tmp_path / "project with spaces"),
            "status": "not_installed",
            "removed_files": [
                ".agents/skills/loopora-plan/SKILL.md",
                ".agents/skills/loopora-run/SKILL.md",
            ],
            "kept_files": [
                {
                    "path": ".agents/skills/loopora-plan/SKILL.md",
                    "reason": "not_loopora_managed",
                }
            ],
            "manifest_error": "invalid manifest",
        },
        action="uninstalled",
        json_output=False,
    )

    output = capsys.readouterr().out

    assert "Codex Loopora entry is uninstalled" in output
    assert "removed files: 2 Loopora-managed files" in output
    assert "removed:" not in output
    assert ".agents/skills/loopora-run/SKILL.md" not in output
    assert "kept files: 1 need manual review" in output
    assert "manual review:" in output
    assert "- .agents/skills/loopora-plan/SKILL.md: not_loopora_managed" in output
    assert "managed manifest was unreadable" in output
    assert "Reinstall later:" in output
    assert "loopora init codex --workdir" in output
    assert "--workdir '" in output
    assert "project with spaces" in output
    assert "refresh or restart Codex" in output
    assert "details: pass --json when you need exact removed and kept paths for cleanup logs." in output


# Merged from test_cli_agent_plan_recovery.py
from loopora.cli_agent_plan_recovery import (
    agent_plan_error_requires_message,
    agent_plan_message_required_result,
    print_agent_plan_message_required,
)


def test_agent_plan_message_required_recovery_keeps_single_question_and_native_surface(tmp_path, capsys) -> None:
    result = agent_plan_message_required_result(
        adapter="codex",
        workdir=tmp_path,
        context_id="ctx_123",
        entry_source="codex_project_skill",
    )

    assert agent_plan_error_requires_message("missing --message task summary") is True
    assert agent_plan_error_requires_message("missing --message task context") is True
    assert agent_plan_error_requires_message("different validation error") is False
    assert result["loop_recovery"] == "plan_message_required"
    assert result["required_inputs"] == [
        "loopora_fit_reason",
        "task_goal",
        "fake_done_risks",
        "required_evidence",
        "judgment_tradeoffs",
    ]
    assert result["question_action"]["target"] == "main_agent_session"
    assert result["question_action"]["subagent_policy"].startswith("Do not ask user questions")
    assert result["task_message_template"].startswith("Loopora fit:")
    assert result["first_task_message_example_state"]["completed_review"] is False
    assert result["first_task_message_example_state"]["kind"] == "generic_orientation_example"
    assert result["first_task_handoff_policy"]["preferred_source"] == "completed_fit_review"
    assert result["first_task_handoff_policy"]["fallback_source"] == "generic_example"
    assert result["first_task_handoff_policy"]["fit_command"].endswith(f"loopora fit --workdir {tmp_path.resolve()}")
    assert "loopora agent codex plan" in result["debug_cli_example_command"]
    assert "--context-id ctx_123" in result["debug_cli_example_command"]
    assert "--entry-source codex_project_skill" in result["debug_cli_example_command"]

    print_agent_plan_message_required(result)
    output = capsys.readouterr().out

    assert output.count("required_inputs:") == 1
    assert "- Loopora fit reason (loopora_fit_reason)" in output
    assert "- Task goal (task_goal)" in output
    assert "ask_user: What long-running task should Loopora govern?" in output
    assert "question_action: Use the host's official user-question or follow-up capability" in output
    assert "recommended_reply_shape: Loopora fit: ..." in output
    assert "Goal: ..." in output
    assert "Fake-done risks: ..." in output
    assert "Required evidence: ..." in output
    assert "Judgment tradeoffs: ..." in output
    assert "decision_impact: This answer decides the Loop's task contract" in output
    assert "example_user_reply: Loopora fit:" in output
    assert "first_task_message_example:" not in output
    assert "debug_cli_example_command:" not in output
    assert "agent_surface: current host Agent remains the executor" in output
    assert "full surface diagnostics are available with --json --compact-json" in output
    assert "agent surface:" not in output
    assert "- host dispatch:" not in output


# Merged from test_cli_agent_plan_repair_hints.py
from loopora.cli_agent_plan_repair_hints import validation_repair_hints


def test_plan_repair_hints_project_host_message_categories_into_runnable_surfaces() -> None:
    hints = validation_repair_hints(
        "Agent-native candidate must project host Agent success criteria into runnable surfaces: missing API compatibility, rollback proof"
    )

    assert hints == [
        "add these missing success criteria categories from --message to runnable plan surfaces: API compatibility, rollback proof",
        "include those categories in spec Done When/Success Surface, role responsibilities, workflow intent, evidence preferences, and GateKeeper closure",
    ]


def test_plan_repair_hints_explain_common_semantic_lint_issues() -> None:
    hints = validation_repair_hints(
        "bundle semantic lint failed: spec must include at least one Done When bullet; workflow.collaboration_intent must explain evidence flow"
    )

    assert "add # Done When bullets that make the task judgment reviewable and runnable" in hints
    assert "rewrite workflow.collaboration_intent to name evidence flow" in hints[1]


# Merged from test_cli_agent_recovery_architecture.py
from pathlib import Path


def test_cli_agent_recovery_has_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    adapter_commands_source = (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(encoding="utf-8")
    native_source = (root / "src" / "loopora" / "cli_agent_native.py").read_text(encoding="utf-8")
    recovery_source = (root / "src" / "loopora" / "cli_agent_recovery.py").read_text(encoding="utf-8")
    run_command_source = (root / "src" / "loopora" / "cli_agent_run_command.py").read_text(encoding="utf-8")
    output_source = (root / "src" / "loopora" / "cli_agent_context_recovery_output.py").read_text(encoding="utf-8")
    results_source = (root / "src" / "loopora" / "cli_agent_recovery_results.py").read_text(encoding="utf-8")
    active_runs_source = (root / "src" / "loopora" / "cli_agent_recovery_active_runs.py").read_text(encoding="utf-8")
    choices_source = (root / "src" / "loopora" / "cli_agent_recoverable_context_output.py").read_text(encoding="utf-8")
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora import cli_agent_recovery as _agent_recovery" in adapter_commands_source
    assert "from loopora.cli_agent_recovery import" in run_command_source
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


# Merged from test_cli_agent_runtime_command_architecture.py


def test_cli_agent_adapter_lifecycle_commands_have_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    adapter_commands_source = (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(encoding="utf-8")
    runtime_commands_source = (root / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(encoding="utf-8")
    lifecycle_source = (root / "src" / "loopora" / "cli_agent_adapter_lifecycle_commands.py").read_text(encoding="utf-8")
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
        "AdapterRuntimeWorkdirOption = Annotated",
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


def test_cli_agent_runtime_phase_commands_have_dedicated_boundaries() -> None:
    root = Path(__file__).resolve().parents[3]
    runtime_source = (root / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(encoding="utf-8")
    phase_sources = {
        phase: (root / "src" / "loopora" / f"cli_agent_{phase}_command.py").read_text(encoding="utf-8") for phase in ("plan", "run", "next", "submit")
    }
    contracts = (root / "design" / "contracts.md").read_text(encoding="utf-8")
    service_boundaries = (root / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    for phase, source in phase_sources.items():
        assert f"from loopora.cli_agent_{phase}_command import" in runtime_source
        assert f"def register_agent_{phase}_command" in source
        assert f"def agent_{phase}" in source
        assert f"def agent_{phase}" not in runtime_source
        assert f"cli_agent_{phase}_command.py" in service_boundaries
    assert "def _claim_agent_next_from_cli_compat" in runtime_source
    assert "claim_agent_next_from_cli(request)" in runtime_source
    assert "Agent Native runtime CLI registration ownership" in contracts
    assert "cli_agent_*_command.py" in contracts


def test_cli_agent_runtime_actions_have_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    adapter_commands_source = (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(encoding="utf-8")
    runtime_commands_source = (root / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(encoding="utf-8")
    phase_sources = "\n".join(
        (root / "src" / "loopora" / f"cli_agent_{phase}_command.py").read_text(encoding="utf-8") for phase in ("plan", "run", "next", "submit")
    )
    actions_source = (root / "src" / "loopora" / "cli_agent_runtime_actions.py").read_text(encoding="utf-8")
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora import cli_agent_runtime_actions as _agent_runtime_actions" in adapter_commands_source
    assert "from loopora.cli_agent_runtime_actions import" in runtime_commands_source
    assert "from loopora.cli_agent_runtime_actions import" in phase_sources
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


def test_cli_agent_runtime_workdir_recovery_has_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    runtime_commands_source = (root / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(encoding="utf-8")
    phase_sources = "\n".join(
        (root / "src" / "loopora" / f"cli_agent_{phase}_command.py").read_text(encoding="utf-8") for phase in ("plan", "run", "next", "submit")
    )
    workdir_recovery_source = (root / "src" / "loopora" / "cli_agent_workdir_recovery.py").read_text(encoding="utf-8")
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_workdir_recovery import" in phase_sources
    for marker in (
        "class AgentRuntimeWorkdirRecoveryRequest",
        "def exit_if_unusable_agent_runtime_workdir",
        "def _agent_runtime_workdir_recovery_json_payload",
        "def _print_agent_runtime_workdir_recovery",
    ):
        assert marker in workdir_recovery_source
        assert marker not in runtime_commands_source
        assert marker not in phase_sources
    assert "cli_agent_workdir_recovery.py" in design_source


# Merged from test_cli_agent_submit_repair_output.py
from loopora.cli_agent_submit_repair_output import print_agent_submit_repair_plain


def test_submit_repair_plain_output_keeps_active_context_and_submitted_dispatch(capsys) -> None:
    print_agent_submit_repair_plain(
        {
            "result_file_to_repair": "/tmp/result.json",
            "active_step_id": "contract_inspection_step",
            "active_role": "Inspector",
            "active_target_agent": "loopora-inspector",
            "active_result_template": "/tmp/contract_inspection.result.template.json",
            "active_result_file_to_write": "/tmp/contract_inspection.result.json",
            "submitted_dispatch": {
                "run_id": "run_001",
                "step_id": "builder_step",
                "iter": 0,
                "step_order": 0,
                "target_agent": "loopora-builder",
                "actual_agent": "loopora-gatekeeper",
                "dispatch_mode": "host_native_role_agent",
                "inline": False,
            },
            "active_known_evidence_ids": ["ev_000_00_builder_step"],
            "active_known_evidence_refs": [
                {
                    "id": "ev_000_00_builder_step",
                    "result": "completed",
                    "gatekeeper_support": "non_supporting",
                    "gatekeeper_support_reason": "no proof artifact",
                    "claim": "Builder proof exists but remains weak.",
                    "coverage_target_ids": ["done_when.check_001", "done_when.check_002"],
                }
            ],
            "active_coverage_target_ids": ["done_when.check_001", "done_when.check_002"],
            "repair_focus": ["submit the active step_id exactly"],
            "next_repair_step": "discard the stale result file and fill the active result template",
            "schema_lookup": "loopora agent codex next --workdir /tmp --run-id run_001 --json",
        }
    )

    output = capsys.readouterr().err

    assert "submit_repair: result JSON needs repair before this Loopora step can advance" in output
    assert "result_file_to_repair: /tmp/result.json" in output
    assert "active_step_id: contract_inspection_step" in output
    assert "active_result_file_to_write: /tmp/contract_inspection.result.json" in output
    assert "submitted_dispatch: run_id=run_001, step_id=builder_step, iter=0, step_order=0" in output
    assert "actual_agent=loopora-gatekeeper" in output
    assert "inline=False" in output
    assert "active_known_evidence_ids:" in output
    assert "- ev_000_00_builder_step result=completed support=non_supporting reason=no proof artifact" in output
    assert "claim: Builder proof exists but remains weak." in output
    assert "coverage_targets: done_when.check_001, done_when.check_002" in output
    assert "active_coverage_target_ids:" in output
    assert "- done_when.check_002" in output
    assert "repair_focus:" in output
    assert "- submit the active step_id exactly" in output
    assert "next_repair_step: discard the stale result file and fill the active result template" in output
    assert "schema_lookup: loopora agent codex next --workdir /tmp --run-id run_001 --json" in output
