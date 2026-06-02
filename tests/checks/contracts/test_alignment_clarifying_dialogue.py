from __future__ import annotations

from pathlib import Path

import pytest

from compacted_contract_support import (
    DEFAULT_EN_ALIGNMENT_MESSAGE,
    DEFAULT_ZH_ALIGNMENT_MESSAGE,
    assert_bundle_not_written,
    assert_first_decision_option_recommended,
    assert_question_reframed,
    latest_assistant_content,
    latest_transcript_message,
    start_waiting_alignment,
)


MIN_CLARIFYING_DECISION_OPTIONS = 2


def test_alignment_service_waits_for_user_question(service_factory, sample_workdir: Path) -> None:
    _service, _created, session = start_waiting_alignment(
        service_factory,
        sample_workdir,
        scenario="alignment_question",
        message=DEFAULT_EN_ALIGNMENT_MESSAGE,
    )
    assistant_message = latest_transcript_message(session)

    assert assistant_message["role"] == "assistant"
    assert "推荐" in assistant_message["content"]
    options = assistant_message["decision_options"]
    assert len(options) >= MIN_CLARIFYING_DECISION_OPTIONS
    assert options[0]["recommended"] is True
    assert "优先阻断假完成" in options[0]["label"]
    assert options[0]["user_reply"]
    assert_bundle_not_written(session)
    assert session["native_resume_available"] is True
    assert session["executor_session_ref"]["session_id"]


def test_alignment_session_start_immediately_string_false_does_not_start(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="alignment_question")

    session = service.create_alignment_session(
        workdir=sample_workdir,
        message=DEFAULT_EN_ALIGNMENT_MESSAGE,
        start_immediately="false",
    )

    assert session["status"] == "idle"
    assert session["transcript"][-1]["role"] == "user"
    assert not Path(session["bundle_path"]).exists()
    events = service.list_alignment_events(session["id"])
    assert not any(event["event_type"] == "alignment_waiting_user" for event in events)


def test_alignment_service_keeps_not_fit_gate_in_dialogue(service_factory, sample_workdir: Path) -> None:
    _service, _created, session = start_waiting_alignment(
        service_factory,
        sample_workdir,
        scenario="alignment_not_fit",
        message="Just run one obvious one-off edit.",
    )

    assert_bundle_not_written(session)
    assert "一次 Agent 执行加一次人工 review" in latest_assistant_content(session)
    assert_first_decision_option_recommended(session)
    assert "Skip Loop" in latest_transcript_message(session)["decision_options"][0]["label"]
    assert session["alignment_stage"] == "clarifying"


def test_alignment_service_keeps_blocked_not_fit_output_in_dialogue(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created, session = start_waiting_alignment(
        service_factory,
        sample_workdir,
        scenario="alignment_not_fit_without_needs_user_input",
        message="Just run one obvious one-off edit.",
    )

    assert_bundle_not_written(session)
    assert session["error_message"] == ""
    assert "反复出现的判断或新证据" in latest_assistant_content(session)
    assert_first_decision_option_recommended(session)
    assert session["alignment_stage"] == "clarifying"
    events = service.list_alignment_events(created["id"])
    assert any(event["event_type"] == "alignment_waiting_user" for event in events)
    assert not any(event["event_type"] == "alignment_failed" for event in events)


@pytest.mark.parametrize(
    ("scenario", "forbidden_text", "expected_issue"),
    [
        ("alignment_mechanical_question", "配置两个 Inspector", "mechanical_configuration_question"),
        ("alignment_generic_preference_question", "你有什么偏好", "generic_alignment_question"),
        ("alignment_questionnaire_overload", "1. 你想完成什么任务", "questionnaire_overload"),
    ],
)
def test_alignment_service_reframes_low_value_questions(
    service_factory,
    sample_workdir: Path,
    scenario: str,
    forbidden_text: str,
    expected_issue: str,
) -> None:
    service, created, session = start_waiting_alignment(
        service_factory,
        sample_workdir,
        scenario=scenario,
        message=DEFAULT_ZH_ALIGNMENT_MESSAGE,
    )
    assistant_message = latest_assistant_content(session)

    assert forbidden_text not in assistant_message
    assert "推荐" in assistant_message
    assert_first_decision_option_recommended(session)
    assert_question_reframed(
        service,
        created["id"],
        {expected_issue, "missing_recommended_decision_options"},
    )
