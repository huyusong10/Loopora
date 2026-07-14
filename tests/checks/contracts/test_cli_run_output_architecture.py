from __future__ import annotations

from pathlib import Path


def test_cli_run_output_has_dedicated_boundary() -> None:
    root = Path(__file__).resolve().parents[3]
    support_source = (root / "src" / "loopora" / "cli_run_support.py").read_text(encoding="utf-8")
    output_source = (root / "src" / "loopora" / "cli_run_output.py").read_text(encoding="utf-8")
    contract_output_source = (root / "src" / "loopora" / "cli_run_contract_output.py").read_text(
        encoding="utf-8"
    )
    task_verdict_output_source = (root / "src" / "loopora" / "cli_task_verdict_output.py").read_text(
        encoding="utf-8"
    )
    step_presenters_source = (root / "src" / "loopora" / "cli_agent_step_presenters.py").read_text(
        encoding="utf-8"
    )
    design_source = (root / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.cli_run_output import" in support_source
    assert "from loopora.cli_run_output import print_run_contract_anchor, print_task_verdict" in step_presenters_source
    assert "from loopora.cli_run_contract_output import print_run_contract_anchor" in output_source
    assert "from loopora.cli_run_contract_output import print_run_contract_summary" in output_source
    assert "from loopora.cli_task_verdict_output import print_task_verdict" in output_source
    assert "def print_run_result" in output_source
    assert "def print_loop_created" in output_source
    assert "def print_run_contract_summary" not in output_source
    assert "def print_task_verdict" not in output_source
    for marker in (
        "def print_run_contract_anchor",
        "def print_run_contract_summary",
        "def _cli_judgment_summary",
    ):
        assert marker in contract_output_source
        assert marker not in support_source + output_source + task_verdict_output_source
    for marker in ("def print_task_verdict", "def _task_verdict_bucket_counts"):
        assert marker in task_verdict_output_source
        assert marker not in support_source + output_source + contract_output_source
    for marker in (
        "def background_worker_command",
        "def spawn_background_worker",
        "class LoopCreateRequest",
        "def create_and_maybe_start_loop",
    ):
        assert marker in support_source
        assert marker not in output_source
    assert "cli_run_output.py" in design_source
    assert "cli_run_contract_output.py" in design_source
    assert "cli_task_verdict_output.py" in design_source
