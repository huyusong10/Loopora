from __future__ import annotations

from web_timeline_projection_test_support import formatted_timeline_event


def test_timeline_run_event_formatter_keeps_stable_observation_details() -> None:
    control_event = formatted_timeline_event(
        "control_triggered",
        {"signal": "no_evidence_progress", "role_id": "inspector"},
    )
    parallel_event = formatted_timeline_event(
        "parallel_group_started",
        {"parallel_group": "inspection_pack", "step_ids": ["review_a", "review_b"]},
    )
    run_finished = formatted_timeline_event(
        "run_finished",
        {
            "status": "succeeded",
            "reason": "rounds_completed",
            "task_verdict_status": "insufficient_evidence",
            "task_verdict_summary": "Required coverage still lacks direct evidence.",
        },
    )
    accepted = formatted_timeline_event(
        "run_result_accepted",
        {"status": "succeeded", "task_verdict_status": "passed"},
    )
    reopened = formatted_timeline_event(
        "run_result_acceptance_reopened",
        {"status": "succeeded", "task_verdict_status": "insufficient_evidence"},
    )
    overflow_iter_finished = formatted_timeline_event(
        "run_finished",
        {"status": "succeeded", "iter": float("inf")},
    )
    legacy_missing_verdict_finished = formatted_timeline_event(
        "run_finished",
        {"status": "succeeded", "reason": "legacy_terminal_event"},
    )

    assert control_event["title"] == "Control triggered"
    assert control_event["detail"] == "no_evidence_progress -> inspector"
    assert parallel_event["title"] == "Parallel review started"
    assert parallel_event["detail"] == "inspection_pack, steps=2"
    assert run_finished["title"] == "Run finished"
    assert (
        run_finished["detail"]
        == "planned rounds completed, task_verdict_status=insufficient_evidence, task_verdict_summary=Required coverage still lacks direct evidence."
    )
    assert accepted["title"] == "Passing evidence verdict recorded"
    assert accepted["detail"] == "status=succeeded, task_verdict_status=passed"
    assert reopened["title"] == "Recorded evidence verdict reopened"
    assert reopened["detail"] == "status=succeeded, task_verdict_status=insufficient_evidence"
    assert overflow_iter_finished["title"] == "Run finished"
    assert overflow_iter_finished["detail"] == "task_verdict_status=not_evaluated"
    assert legacy_missing_verdict_finished["title"] == "Run finished"
    assert legacy_missing_verdict_finished["detail"] == "legacy_terminal_event, task_verdict_status=not_evaluated"
