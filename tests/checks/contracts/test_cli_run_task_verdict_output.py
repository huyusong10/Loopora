from __future__ import annotations

from pathlib import Path

from cli_run_output_test_support import print_run_result_output


def test_cli_run_result_separates_run_status_and_task_verdict(capsys, tmp_path: Path) -> None:
    output = print_run_result_output(
        capsys,
        {
            "id": "run_contract",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_contract"),
            "task_verdict": {
                "status": "insufficient_evidence",
                "source": "rounds_completion",
                "summary": "The run ended, but evidence is still too thin.",
            },
        },
    )

    assert "run_status: succeeded" in output
    assert "task_verdict: insufficient_evidence" in output
    assert "task_verdict_source: rounds_completion" in output
    assert "task_verdict_summary: The run ended, but evidence is still too thin." in output


def test_cli_run_result_explains_passing_verdict_audit_buckets(capsys, tmp_path: Path) -> None:
    output = print_run_result_output(
        capsys,
        {
            "id": "run_passed_with_audit_buckets",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_passed_with_audit_buckets"),
            "task_verdict": {
                "status": "passed",
                "source": "gatekeeper",
                "summary": "Required evidence passed.",
                "buckets": {
                    "proven": [{"id": "done_when.check_001", "label": "Required proof", "required": True}],
                    "weak": [{"label": "Earlier weak evidence remains visible."}],
                    "unproven": [{"id": "fake_done.risk_001", "label": "Advisory fake-done risk", "required": False}],
                    "blocking": [],
                    "residual_risk": [{"label": "Tracked follow-up.", "managed": True}],
                },
            },
        },
    )

    assert "task_verdict: passed" in output
    assert "task_verdict_buckets: proven 1 / weak 1 / unproven 1 / blocking 0 / residual_risk 1" in output
    assert "task_verdict_required_basis: 1/1 required targets proven; blocking 0" in output
    assert "task_verdict_bucket_note: passing verdict kept non-blocking" in output
    assert "for audit or accepted follow-up" in output
    assert "required coverage and GateKeeper support still passed" in output


def test_cli_run_result_prints_not_evaluated_when_task_verdict_is_missing(capsys, tmp_path: Path) -> None:
    output = print_run_result_output(
        capsys,
        {
            "id": "run_legacy",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_legacy"),
        },
    )

    assert "run_status: succeeded" in output
    assert "task_verdict: not_evaluated" in output
