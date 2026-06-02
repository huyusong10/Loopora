from __future__ import annotations

from loopora.service_alignment_execution import (
    alignment_executor_output_action,
    alignment_executor_output_failure_message,
    alignment_executor_output_waits_for_user,
)


def test_alignment_executor_output_action_prioritizes_bundle_before_waiting_user() -> None:
    assert (
        alignment_executor_output_action(
            {"needs_user_input": True, "alignment_phase": "blocked"},
            assistant_message="I still have a question.",
            bundle_yaml="version: 1\n",
        )
        == "bundle"
    )


def test_alignment_executor_output_action_waits_for_user_on_explicit_need_or_blocked_message() -> None:
    assert alignment_executor_output_action({"needs_user_input": True}, assistant_message="", bundle_yaml="") == "waiting_user"
    assert (
        alignment_executor_output_action(
            {"status": "blocked"},
            assistant_message="This task does not fit a Loop.",
            bundle_yaml="",
        )
        == "waiting_user"
    )
    assert alignment_executor_output_waits_for_user({"alignment_phase": "blocked"}, assistant_message="Need a decision.") is True
    assert alignment_executor_output_waits_for_user({"alignment_phase": "blocked"}, assistant_message="") is False


def test_alignment_executor_output_action_fails_without_bundle_or_user_wait() -> None:
    assert alignment_executor_output_action({}, assistant_message="", bundle_yaml="") == "failed"
    assert alignment_executor_output_failure_message("") == "Agent finished without a bundle or a clarifying question."
    assert alignment_executor_output_failure_message("Done without bundle.") == "Done without bundle."
