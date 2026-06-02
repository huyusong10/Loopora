from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_cli_agent_outputs_use_guidance_instead_of_submitted_step_private_wrappers() -> None:
    offenders = []
    for name in ("cli_agent_current_step_output.py", "cli_agent_step_presenters.py"):
        path = REPO_ROOT / "src" / "loopora" / name
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != "loopora.cli_agent_submitted_step_output":
                continue
            if any(alias.name in {"_actionable_blocking_item", "_actionable_next_action"} for alias in node.names):
                offenders.append(name)

    assert offenders == []


def test_cli_agent_current_step_known_evidence_output_has_dedicated_boundary() -> None:
    current_step_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_output.py").read_text(
        encoding="utf-8"
    )
    evidence_output_source = (
        REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_evidence_output.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_current_step_evidence_output import" in current_step_source
    for marker in (
        "def print_agent_current_step_evidence_scope",
        "def print_agent_current_step_known_evidence",
        "def print_agent_current_step_known_evidence_refs",
        "def _format_known_evidence_artifact_refs",
    ):
        assert marker in evidence_output_source
        assert marker not in current_step_source
    assert "agent_known_evidence_ref_summaries" in evidence_output_source
    assert "agent_known_evidence_ref_summaries" not in current_step_source
    assert "cli_agent_current_step_evidence_output.py" in design_source


def test_cli_agent_current_step_continuation_output_has_dedicated_boundary() -> None:
    current_step_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_output.py").read_text(
        encoding="utf-8"
    )
    continuation_output_source = (
        REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_continuation_output.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_current_step_continuation_output import" in current_step_source
    for marker in (
        "def print_agent_continuation",
        "def _print_continuation_coverage",
        "def _print_continuation_next_focus",
        "def _print_continuation_focus_items",
    ):
        assert marker in continuation_output_source
        assert marker not in current_step_source
    assert "continuation_previous_run" in continuation_output_source
    assert "continuation_previous_run" not in current_step_source
    assert "cli_agent_current_step_continuation_output.py" in design_source


def test_cli_agent_current_step_iteration_output_has_dedicated_boundary() -> None:
    current_step_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_output.py").read_text(
        encoding="utf-8"
    )
    iteration_output_source = (
        REPO_ROOT / "src" / "loopora" / "cli_agent_current_step_iteration_output.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_current_step_iteration_output import" in current_step_source
    for marker in (
        "def print_agent_iteration_context",
        "def _print_agent_iteration_repair",
        "iteration_repair_next_action",
        "iteration_repair_evidence_refs",
    ):
        assert marker in iteration_output_source
        assert marker not in current_step_source
    assert "actionable_next_action" in iteration_output_source
    assert "actionable_next_action" not in current_step_source
    assert "cli_agent_current_step_iteration_output.py" in design_source


def test_cli_agent_step_results_have_dedicated_boundary() -> None:
    presenters_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_step_presenters.py").read_text(
        encoding="utf-8"
    )
    results_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_step_results.py").read_text(encoding="utf-8")
    submit_results_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_submit_results.py").read_text(
        encoding="utf-8"
    )
    adapter_commands_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(
        encoding="utf-8"
    )
    runtime_commands_source = (REPO_ROOT / "src" / "loopora" / "cli_agent_runtime_commands.py").read_text(
        encoding="utf-8"
    )
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_agent_step_results import" in presenters_source
    assert "from loopora.cli_agent_submit_results import" in presenters_source
    assert "from loopora import cli_agent_step_presenters as _agent_step_presenters" in adapter_commands_source
    assert "from loopora.cli_agent_step_presenters import" in runtime_commands_source
    for marker in (
        "def _attach_agent_run_summary",
        "def _agent_next_json_payload",
        "def _agent_next_summary",
    ):
        assert marker in results_source
        assert marker not in presenters_source
        assert marker not in submit_results_source
    for marker in (
        "def _agent_submit_json_payload",
        "def _agent_submit_summary",
        "def _agent_submitted_step_summary",
    ):
        assert marker in submit_results_source
        assert marker not in presenters_source
        assert marker not in results_source
    for marker in (
        "def _print_agent_loop_result",
        "def _print_agent_step_result",
        "def _print_agent_next_result",
    ):
        assert marker in presenters_source
        assert marker not in results_source
    assert "cli_agent_step_results.py" in design_source
    assert "cli_agent_submit_results.py" in design_source
    assert "cli_agent_runtime_commands.py" in design_source
