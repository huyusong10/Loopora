from __future__ import annotations

from agent_adapter_test_support import cli_agent_adapter_commands


def test_agent_cli_required_coverage_summary_labels_partial_as_evidence_status() -> None:
    summary = cli_agent_adapter_commands._required_coverage_summary(
        {
            "status": "partial",
            "covered_check_count": 0,
            "missing_check_count": 5,
        }
    )

    assert summary == "partial evidence; required checks 0 covered / 5 missing"


def test_agent_cli_required_coverage_summary_includes_target_counts() -> None:
    summary = cli_agent_adapter_commands._required_coverage_summary(
        {
            "status": "blocked",
            "covered_check_count": 5,
            "missing_check_count": 0,
            "target_count": 13,
            "covered_target_count": 5,
            "missing_target_count": 7,
            "blocked_target_count": 1,
        }
    )

    assert summary == "blocked; required checks 5 covered / 0 missing, 5/13 targets covered / 7 missing / 1 blocked"


def test_agent_cli_top_coverage_gaps_marks_blocking_status(capsys) -> None:
    cli_agent_adapter_commands._print_top_coverage_gaps(
        {
            "top_gaps": [
                {
                    "target_id": "done_when.check_001",
                    "status": "blocked",
                    "source_section": "Done When",
                    "text": "Admin permission still lacks proof.",
                }
            ]
        }
    )

    assert "- done_when.check_001: [blocked] [Done When] Admin permission still lacks proof." in capsys.readouterr().out
