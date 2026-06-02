from __future__ import annotations

import pytest

from loopora.strategy_controls import strategy_control_after_seconds, strategy_iteration_control_triggers


ONE_HOUR_SECONDS = 3600.0
THREE_MINUTES_SECONDS = 180.0
TWO_SECONDS = 2.0
FIVE_HUNDRED_MS_SECONDS = 0.5


def test_strategy_control_after_seconds_parses_supported_units() -> None:
    assert strategy_control_after_seconds("500ms") == FIVE_HUNDRED_MS_SECONDS
    assert strategy_control_after_seconds("2s") == TWO_SECONDS
    assert strategy_control_after_seconds("3m") == THREE_MINUTES_SECONDS
    assert strategy_control_after_seconds("1h") == ONE_HOUR_SECONDS
    assert strategy_control_after_seconds("not-a-duration") == 0.0


def test_strategy_iteration_control_triggers_cover_rejection_and_required_coverage_stall() -> None:
    triggers = strategy_iteration_control_triggers(
        {"passed": False, "evidence_refs": ["ev_001"]},
        {
            "stagnation_mode": "none",
            "evidence_progress_mode": "stalled",
            "latest_missing_check_count": 2,
        },
    )

    assert [trigger.signal for trigger in triggers] == ["gatekeeper_rejected", "no_evidence_progress"]
    assert triggers[0].trigger["evidence_refs"] == ["ev_001"]
    assert triggers[1].trigger["evidence_progress_mode"] == "stalled"
    assert "Required coverage did not improve" in str(triggers[1].trigger["reason"])


@pytest.mark.parametrize("missing_check_count", [True, "2", 1.5])
def test_strategy_iteration_control_triggers_do_not_promote_corrupt_missing_counts(missing_check_count) -> None:
    triggers = strategy_iteration_control_triggers(
        None,
        {
            "stagnation_mode": "none",
            "evidence_progress_mode": "stalled",
            "latest_missing_check_count": missing_check_count,
        },
    )

    assert [trigger.signal for trigger in triggers] == ["no_evidence_progress"]
    assert triggers[0].trigger["reason"] == "Required coverage did not improve; missing checks: 0."


def test_strategy_iteration_control_triggers_skip_clean_iteration() -> None:
    assert strategy_iteration_control_triggers({"passed": True, "evidence_refs": ["ev_001"]}, {"stagnation_mode": "none"}) == []
