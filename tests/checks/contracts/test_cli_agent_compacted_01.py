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
    assert_output_contains,
    codex_installed_mutation_result,
    native_surface_boundary_snippets,
    packaging_surface_snippets,
)


def test_adapter_output_keeps_native_surface_and_clean_fallback_steps(tmp_path, capsys) -> None:
    print_adapter_mutation_result(
        codex_installed_mutation_result(tmp_path),
        action="installed",
        json_output=False,
    )

    output = capsys.readouterr().out

    assert "Codex Loopora entry is installed" in output
    assert "target project:" in output
    assert "first task message example:" in output
    assert "agent surface:" in output
    assert "- slash commands: plan=/loopora-plan run=/loopora-run" in output
    assert_output_contains(
        output,
        "- capabilities: execution=current_host_agent",
        "role_dispatch=host_native",
        "workspace=current_host_agent_workdir",
        "worktree=not_created_or_switched_by_loopora",
        "proof=loopora_evidence_refs_and_task_verdict",
    )
    assert "- activation: explicit_loopora_command_or_cli_only" in output
    assert "- command namespace: loopora_plan_run_only_no_generic_host_command_aliases" in output
    assert "- references: .agents/skills/loopora-run/references/loopora-run-contract.md" in output
    for snippet in packaging_surface_snippets():
        assert snippet in output
    assert_output_contains(output, *native_surface_boundary_snippets())
    assert "{label}" not in output
    assert "managed files:" in output

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
    assert agent_plan_error_requires_message("different validation error") is False
    assert result["loop_recovery"] == "plan_message_required"
    assert result["required_inputs"] == ["task_goal", "fake_done_risks", "required_evidence", "judgment_tradeoffs"]
    assert result["question_action"]["target"] == "main_agent_session"
    assert result["question_action"]["subagent_policy"].startswith("Do not ask user questions")
    assert result["task_message_template"].startswith("Goal:")
    assert "loopora agent codex plan" in result["debug_cli_example_command"]
    assert "--context-id ctx_123" in result["debug_cli_example_command"]
    assert "--entry-source codex_project_skill" in result["debug_cli_example_command"]

    print_agent_plan_message_required(result)
    output = capsys.readouterr().out

    assert output.count("required_inputs:") == 1
    assert "ask_user: What long-running task should Loopora govern?" in output
    assert "question_action: Use the host's official user-question or follow-up capability" in output
    assert "recommended_reply_shape: Goal: ..." in output
    assert "Fake-done risks: ..." in output
    assert "Required evidence: ..." in output
    assert "Judgment tradeoffs: ..." in output
    assert "decision_impact: This answer decides the Loop's task contract" in output
    assert "example_user_reply: Build the account-deletion audit flow;" in output
    assert "first_task_message_example:" not in output
    assert "debug_cli_example_command:" not in output
    assert "agent surface:" in output
    assert "- host dispatch: Codex spawn_agent with agent_type=<role_dispatch.target_agent>" in output

# Merged from test_cli_agent_plan_repair_hints.py
from loopora.cli_agent_plan_repair_hints import validation_repair_hints


def test_plan_repair_hints_project_host_message_categories_into_runnable_surfaces() -> None:
    hints = validation_repair_hints(
        "agent-first candidate must project host Agent success criteria into runnable surfaces: "
        "missing API compatibility, rollback proof"
    )

    assert hints == [
        "add these missing success criteria categories from --message to runnable plan surfaces: API compatibility, rollback proof",
        "include those categories in spec Done When/Success Surface, role responsibilities, workflow intent, evidence preferences, and GateKeeper closure",
    ]


def test_plan_repair_hints_explain_common_semantic_lint_issues() -> None:
    hints = validation_repair_hints(
        "bundle semantic lint failed: spec must include at least one Done When bullet; "
        "workflow.collaboration_intent must explain evidence flow"
    )

    assert "add # Done When bullets that make the task judgment reviewable and runnable" in hints
    assert "rewrite workflow.collaboration_intent to name evidence flow" in hints[1]

# Merged from test_cli_agent_recovery_architecture.py
from pathlib import Path


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

# Merged from test_cli_agent_runtime_command_architecture.py


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
