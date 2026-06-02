from __future__ import annotations

from loopora.agent_native_task_proof import (
    agent_native_task_next_action,
    agent_task_proof_summary,
    with_agent_native_judgment_contract,
)
from loopora.task_verdicts import PASSING_TASK_VERDICT_STATUSES


def test_agent_task_proof_summary_treats_residual_risk_pass_as_proven() -> None:
    assert frozenset({"passed", "passed_with_residual_risk"}) == PASSING_TASK_VERDICT_STATUSES

    summary = agent_task_proof_summary(
        complete=True,
        task_verdict_status="passed_with_residual_risk",
        task_verdict_summary="Residual risk is accepted and named in the task verdict.",
        task_next_action={},
    )

    assert summary == {
        "task_proven": True,
        "task_outcome": "proven",
        "lifecycle_vs_task": "run_lifecycle_complete_task_proven",
        "task_proof_source": "run.task_verdict",
        "run_lifecycle_source": "result.complete",
    }


def test_agent_native_task_next_action_routes_terminal_unproven_runs_to_new_evidence_pass() -> None:
    action = agent_native_task_next_action(
        {
            "complete": True,
            "run": {
                "run_status": "succeeded",
                "task_verdict": {
                    "status": "insufficient_evidence",
                    "summary": "Browser proof is missing.",
                },
            },
        }
    )

    assert action["kind"] == "continue_evidence"
    assert action["reason"] == "run_lifecycle_complete_task_not_proven"
    assert action["next_loop_command"] == "/loopora-run"
    assert action["task_verdict_summary"] == "Browser proof is missing."


def test_agent_native_task_next_action_stops_terminal_passed_replay() -> None:
    action = agent_native_task_next_action(
        {
            "complete": True,
            "run": {
                "status": "succeeded",
                "task_verdict_json": {
                    "status": "passed_with_residual_risk",
                    "summary": "Residual risk is named and accepted.",
                },
            },
        }
    )

    assert action["kind"] == "already_passed"
    assert action["reason"] == "task_verdict_passed"
    assert action["task_verdict_status"] == "passed_with_residual_risk"
    assert "no new evidence pass" in action["guidance"]


def test_with_agent_native_judgment_contract_attaches_task_next_action() -> None:
    result = with_agent_native_judgment_contract(
        {
            "complete": True,
            "run": {
                "status": "succeeded",
                "task_verdict_json": {"status": "failed", "summary": "Rollback proof is missing."},
            },
        }
    )

    assert "judgment_contract" in result
    assert result["task_next_action"]["kind"] == "continue_evidence"
    assert result["task_next_action"]["task_verdict_summary"] == "Rollback proof is missing."


def test_agent_task_proof_summary_distinguishes_lifecycle_complete_from_unproven_task() -> None:
    summary = agent_task_proof_summary(
        complete=True,
        task_verdict_status="insufficient_evidence",
        task_verdict_summary="Audit proof is still missing.",
        task_next_action={
            "kind": "continue_evidence",
            "next_loop_command": "/loopora-run",
        },
    )

    assert summary["task_proven"] is False
    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["lifecycle_vs_task"] == "run_lifecycle_complete_task_not_proven"
    assert summary["next_loop_command"] == "/loopora-run"
    assert summary["next_evidence_focus"] == "Audit proof is still missing."


def test_agent_task_proof_summary_allows_cli_to_compact_next_evidence_focus() -> None:
    summary = agent_task_proof_summary(
        complete=False,
        task_verdict_status="failed",
        task_verdict_summary="Line one\n\nLine two requires follow-up.",
        task_next_action={},
        normalize_next_evidence_focus=lambda value: " ".join(value.split()),
    )

    assert summary["task_outcome"] == "not_proven_continue_evidence"
    assert summary["next_evidence_focus"] == "Line one Line two requires follow-up."
