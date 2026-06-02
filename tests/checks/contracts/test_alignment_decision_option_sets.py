from __future__ import annotations

from loopora.service_alignment_decision_options import (
    agreement_confirmation_decision_options,
    default_alignment_decision_options,
    not_fit_alignment_decision_options,
)


def test_alignment_decision_option_sets_keep_stable_ids_and_recommendations() -> None:
    assert [option["id"] for option in default_alignment_decision_options(prefers_chinese=False)] == [
        "evidence_first",
        "speed_first",
        "add_judgment",
    ]
    assert default_alignment_decision_options(prefers_chinese=True)[0]["recommended"] is True
    assert [option["id"] for option in agreement_confirmation_decision_options(prefers_chinese=False)] == [
        "confirm_agreement",
        "adjust_agreement",
    ]
    assert [option["id"] for option in not_fit_alignment_decision_options(prefers_chinese=True)] == [
        "skip_loop",
        "still_compile",
    ]
