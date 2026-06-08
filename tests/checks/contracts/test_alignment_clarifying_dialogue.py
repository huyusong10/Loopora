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
from loopora.service_alignment_agreement_stage import alignment_message_selects_skip_loop


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


def test_alignment_service_recommends_skip_loop_when_default_path_detects_one_off_task(
    service_factory,
    sample_workdir: Path,
) -> None:
    service, created, session = start_waiting_alignment(
        service_factory,
        sample_workdir,
        scenario="success",
        message="请帮我把 README 里的一个错别字修掉。只要现有检查通过就算完成；这是一次性小修，不需要后续轮次或新证据。",
    )
    assistant_message = latest_transcript_message(session)

    assert_bundle_not_written(session)
    assert session["alignment_stage"] == "clarifying"
    assert "不适合先编排成 Loop" in latest_assistant_content(session)
    assert assistant_message["missing_items"] == ["loop_fit"]
    assert [option["id"] for option in assistant_message["decision_options"]] == ["skip_loop", "still_compile"]
    assert assistant_message["decision_options"][0]["recommended"] is True

    skipped = service.append_alignment_message(
        created["id"],
        assistant_message["decision_options"][0]["user_reply"],
    )

    assert skipped["status"] == "skipped"
    assert_bundle_not_written(skipped)
    assert "不会写入 bundle，也不会启动运行" in latest_assistant_content(skipped)


def test_alignment_service_respects_skip_loop_choice_without_reasking(service_factory, sample_workdir: Path) -> None:
    service, created, session = start_waiting_alignment(
        service_factory,
        sample_workdir,
        scenario="alignment_not_fit",
        message="Just run one obvious one-off edit.",
    )
    started_before = [
        event for event in service.list_alignment_events(created["id"]) if event["event_type"] == "alignment_started"
    ]

    skipped = service.append_alignment_message(
        created["id"],
        latest_transcript_message(session)["decision_options"][0]["user_reply"],
    )

    assert skipped["status"] == "skipped"
    assert skipped["alignment_stage"] == "clarifying"
    assert_bundle_not_written(skipped)
    assert latest_transcript_message(skipped)["role"] == "assistant"
    assert "won't generate a Loop plan" in latest_assistant_content(skipped)
    events = service.list_alignment_events(created["id"])
    assert [event for event in events if event["event_type"] == "alignment_started"] == started_before
    assert any(
        event["event_type"] == "alignment_skipped"
        and event["payload"].get("reason") == "user_selected_skip_loop"
        for event in events
    )


def test_alignment_skip_loop_choice_accepts_not_fit_review_without_options() -> None:
    session = {
        "transcript": [
            {
                "role": "assistant",
                "content": "Loopora 已把这次 /loopora-plan 打开为 Web review；不会伪装成可运行 Loop。",
            }
        ]
    }

    assert alignment_message_selects_skip_loop(session, "同意，先不生成 Loop 方案。")


def test_alignment_skip_loop_choice_accepts_legacy_not_fit_option_id() -> None:
    session = {
        "transcript": [
            {
                "role": "assistant",
                "content": "这不适合 Loopora。",
                "decision_options": [
                    {
                        "id": "end_loopora_plan",
                        "label": "先结束",
                        "description": "不生成 Loop。",
                        "recommended": True,
                        "user_reply": "结束 /loopora-plan，不生成 Loop。",
                    },
                    {
                        "id": "redefine_as_loop",
                        "label": "重新定义",
                        "description": "补充后续轮次需要继承的判断。",
                        "recommended": False,
                        "user_reply": "仍然需要 Loop，因为：",
                    },
                ],
            }
        ]
    }

    assert alignment_message_selects_skip_loop(session, "结束 /loopora-plan，不生成 Loop；请直接处理。")


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
