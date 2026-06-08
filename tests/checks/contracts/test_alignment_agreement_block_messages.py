from __future__ import annotations

from loopora.service_alignment_decision_options import default_alignment_decision_options
from loopora.service_alignment_decision_options import not_fit_alignment_decision_options
from loopora.service_alignment_stage import (
    AlignmentAgreementBlockCandidate,
    alignment_agreement_block_plan,
    alignment_block_message,
    alignment_missing_items_followup_question,
)


def test_alignment_agreement_block_plan_selects_first_issue_group() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=[],
                event_type="alignment_checklist_incomplete",
                fallback_message="缺少：{missing}",
            ),
            AlignmentAgreementBlockCandidate(
                issues=["loop_fit", "task_scope"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少证据：{missing}",
            ),
            AlignmentAgreementBlockCandidate(
                issues=["agreement_summary"],
                event_type="alignment_language_mismatch",
                fallback_message="缺少语言：{missing}",
            ),
        ],
        prefers_chinese=True,
    )

    assert plan is not None
    assert plan.event_type == "alignment_evidence_incomplete"
    assert plan.event_payload == {
        "alignment_stage": "clarifying",
        "missing": ["loop_fit", "task_scope"],
    }
    assert plan.output_updates["alignment_phase"] == "clarifying"
    assert plan.output_updates["agreement_summary"] == ""
    assert plan.output_updates["bundle_yaml"] == ""
    assert plan.output_updates["needs_user_input"] is True
    assert plan.output_updates["alignment_missing_items"] == ["loop_fit", "task_scope"]
    assert plan.output_updates["decision_options"] == default_alignment_decision_options(prefers_chinese=True)
    assert plan.output_updates["assistant_message"].startswith("缺少证据：是否适合 Loopora, 任务范围")
    assert "后续轮次会产生什么一次 Agent 执行不会产生的新证据或交接" in plan.output_updates["assistant_message"]


def test_alignment_agreement_block_plan_replaces_stale_confirmation_options() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=["local_governance"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少证据：{missing}",
            ),
        ],
        prefers_chinese=True,
    )

    assert plan is not None
    assert [option["id"] for option in plan.output_updates["decision_options"]] == [
        "evidence_first",
        "speed_first",
        "add_judgment",
    ]
    assert "confirm_agreement" not in {option["id"] for option in plan.output_updates["decision_options"]}


def test_alignment_agreement_block_plan_recommends_skip_for_loop_fit_contradiction() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=["loop_fit"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少证据：{missing}",
            ),
        ],
        prefers_chinese=True,
        not_fit_source_text="这是一次性小修，不需要后续轮次或新证据。",
    )

    assert plan is not None
    assert plan.output_updates["decision_options"] == not_fit_alignment_decision_options(prefers_chinese=True)
    assert plan.output_updates["decision_options"][0]["id"] == "skip_loop"
    assert "不适合先编排成 Loop" in plan.output_updates["assistant_message"]


def test_alignment_agreement_block_plan_uses_event_semantics_for_english_messages() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=["readiness_evidence"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少：{missing}",
            ),
        ],
        prefers_chinese=False,
    )

    assert plan is not None
    assert "readiness evidence is not specific enough: readiness evidence" in plan.output_updates["assistant_message"]
    assert "What concrete evidence should prove" in plan.output_updates["assistant_message"]


def test_alignment_agreement_block_plan_returns_none_without_issues() -> None:
    assert (
        alignment_agreement_block_plan(
            [
                AlignmentAgreementBlockCandidate(
                    issues=[],
                    event_type="alignment_checklist_incomplete",
                    fallback_message="缺少：{missing}",
                ),
            ],
            prefers_chinese=True,
        )
        is None
    )


def test_alignment_block_message_uses_language_and_event_semantics() -> None:
    chinese_message = alignment_block_message(
        prefers_chinese=True,
        event_type="alignment_evidence_incomplete",
        missing=["loop_fit"],
        fallback_zh="缺少：{missing}",
    )
    assert chinese_message.startswith("缺少：是否适合 Loopora")
    assert "后续轮次会产生什么一次 Agent 执行不会产生的新证据或交接" in chinese_message

    evidence_message = alignment_block_message(
        prefers_chinese=False,
        event_type="alignment_evidence_incomplete",
        missing=["loop_fit"],
        fallback_zh="缺少：{missing}",
    )
    language_message = alignment_block_message(
        prefers_chinese=False,
        event_type="alignment_language_mismatch",
        missing=["agreement_summary"],
        fallback_zh="缺少：{missing}",
    )

    assert "readiness evidence is not specific enough: Loopora fit" in evidence_message
    assert "What new evidence or handoff" in evidence_message
    assert "user-facing agreement fields need the user's language: agreement summary" in language_message


def test_alignment_block_message_keeps_stable_missing_ids_in_event_payload_but_not_user_copy() -> None:
    plan = alignment_agreement_block_plan(
        [
            AlignmentAgreementBlockCandidate(
                issues=["workdir_facts"],
                event_type="alignment_evidence_incomplete",
                fallback_message="缺少证据：{missing}",
            ),
        ],
        prefers_chinese=True,
    )

    assert plan is not None
    assert "运行目录/项目事实" in plan.output_updates["assistant_message"]
    assert "workdir_facts" not in plan.output_updates["assistant_message"]
    assert plan.event_payload["missing"] == ["workdir_facts"]


def test_alignment_block_message_asks_specific_loop_shaping_question_for_missing_success_surface() -> None:
    message = alignment_block_message(
        prefers_chinese=True,
        event_type="alignment_evidence_incomplete",
        missing=["success_surface"],
        fallback_zh="我还不能整理确认协议；这些对齐证据还不够具体：{missing}。",
    )

    assert "成功面" in message
    assert "下一步请回答" in message
    assert "必须证明哪个具体的用户可见结果或可审计结果" in message
    assert "补一个会改变 Loop 方案的问题" not in message


def test_alignment_block_message_translates_evidence_bucket_missing_item_for_users() -> None:
    message = alignment_block_message(
        prefers_chinese=True,
        event_type="alignment_evidence_incomplete",
        missing=["evidence_buckets"],
        fallback_zh="我还不能整理确认协议；这些对齐证据还不够具体：{missing}。",
    )

    assert "证据分级" in message
    assert "evidence buckets" not in message
    assert "已证明、弱证据、未证明、阻断或残余风险" in message


def test_alignment_block_message_asks_refactor_specific_question_for_improvement_delta() -> None:
    message = alignment_block_message(
        prefers_chinese=True,
        event_type="alignment_improvement_incomplete",
        missing=["improvement_refactor_delta"],
        fallback_zh="我还不能整理改进协议；这些基于已有方案的改进判断还不够具体：{missing}。",
    )

    assert "任务范围内的重构 delta" in message
    assert "improvement_refactor_delta" not in message
    assert "复杂度没有只是换地方" in message
    assert "用户行为没有回归" in message
    assert "证据路径可复验" in message


def test_alignment_missing_items_followup_question_prioritizes_first_missing_item() -> None:
    assert alignment_missing_items_followup_question(
        ["success_surface", "fake_done_risks"],
        prefers_chinese=False,
    ).startswith("When this is done")
