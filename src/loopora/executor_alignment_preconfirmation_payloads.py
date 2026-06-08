from __future__ import annotations

from dataclasses import dataclass

from loopora.executor_alignment_bundle_fixtures import alignment_bundle_yaml
from loopora.executor_alignment_agreement_responses import (
    alignment_agreement_response,
    alignment_chinese_agreement_response,
    alignment_chinese_improvement_agreement_response,
    alignment_chinese_refund_agreement_response,
    alignment_improvement_agreement_response,
    alignment_refund_agreement_response,
)
from loopora.executor_alignment_responses import (
    alignment_response,
)


@dataclass(frozen=True)
class AlignmentPreconfirmationPayloadRequest:
    mode: str
    alignment_stage: str
    workdir: str
    prefers_chinese: bool
    is_improvement: bool


def alignment_preconfirmation_payload_for_scenario(
    scenario: str,
    *,
    request: AlignmentPreconfirmationPayloadRequest,
) -> dict | None:
    payload = _alignment_preconfirmation_scenario_payload(scenario, workdir=request.workdir)
    if payload is not None:
        return payload
    if request.mode != "repair" and request.alignment_stage not in {
        "confirmed",
        "compiling",
        "ready_review",
    }:
        return _alignment_preconfirmation_agreement_payload_for_scenario(
            scenario,
            prefers_chinese=request.prefers_chinese,
            is_improvement=request.is_improvement,
        )
    return None


def _alignment_preconfirmation_scenario_payload(scenario: str, *, workdir: str) -> dict | None:
    status = "question"
    assistant_message = ""
    needs_user_input = True
    bundle_yaml = ""
    phase = "clarifying"
    decision_options: list[dict] | None = None
    if scenario == "alignment_question":
        assistant_message = "我建议先按“证据不足不能通过”来编排，这样结果可以小一点，但不会只靠表面完成过关。你可以直接采用推荐，或改成更偏速度。"
        decision_options = [
            {
                "id": "evidence_first",
                "label": "优先阻断假完成（推荐）",
                "description": "少做一点也可以，但必须证明核心路径真的成立。",
                "recommended": True,
                "user_reply": "采用推荐：优先阻断看起来完成但证据不足的结果，少而真实也可以。",
            },
            {
                "id": "speed_first",
                "label": "优先快速推进",
                "description": "先交一个更务实的首版，允许部分残余风险保持可见。",
                "recommended": False,
                "user_reply": "我选择优先快速推进，可以接受部分残余风险保持可见。",
            },
        ]
    elif scenario == "alignment_not_fit":
        status = "blocked"
        assistant_message = "这看起来一次 Agent 执行加一次人工 review 就够了；如果你仍想用 Loopora，请说明会反复出现的判断或新证据。"
        phase = "blocked"
    elif scenario == "alignment_not_fit_without_needs_user_input":
        status = "blocked"
        assistant_message = "这看起来一次 Agent 执行加一次人工 review 就够了；如果你仍想用 Loopora，请说明会反复出现的判断或新证据。"
        needs_user_input = False
        phase = "blocked"
    elif scenario == "alignment_mechanical_question":
        assistant_message = "你要不要配置两个 Inspector、一个 GateKeeper 和高级 workflow 字段？"
    elif scenario == "alignment_generic_preference_question":
        assistant_message = "你有什么偏好？你想要高质量还是快一点？"
    elif scenario == "alignment_questionnaire_overload":
        assistant_message = "请先回答这些问题：\n1. 你想完成什么任务？\n2. 你希望什么证据能证明完成？\n3. 你能接受哪些残余风险？\n4. 你希望角色怎么分工？"
    elif scenario == "alignment_english_clarifying_message_for_chinese_user":
        assistant_message = "What evidence should prove completion before I compile the Loop?"
    elif scenario == "alignment_premature_bundle":
        status = "bundle"
        assistant_message = "我跳过对齐直接生成 bundle。"
        needs_user_input = False
        bundle_yaml = alignment_bundle_yaml(workdir)
    else:
        return None
    payload = alignment_response(
        status=status,
        assistant_message=assistant_message,
        needs_user_input=needs_user_input,
        bundle_yaml=bundle_yaml,
        phase=phase,
    )
    if decision_options:
        payload["decision_options"] = decision_options
    return payload


def _alignment_preconfirmation_agreement_payload_for_scenario(
    scenario: str,
    *,
    prefers_chinese: bool,
    is_improvement: bool,
) -> dict:
    if is_improvement and scenario != "alignment_improvement_missing_delta":
        payload = alignment_chinese_improvement_agreement_response() if prefers_chinese else alignment_improvement_agreement_response()
    elif scenario in {"alignment_chinese_refund_agreement_generic_bundle", "alignment_chinese_refund_agreement_repair_bundle"}:
        payload = alignment_chinese_refund_agreement_response()
    elif scenario in {"alignment_refund_agreement_generic_bundle", "alignment_refund_agreement_repair_bundle"}:
        payload = alignment_refund_agreement_response()
    else:
        payload = alignment_chinese_agreement_response() if prefers_chinese else alignment_agreement_response()
    if scenario == "alignment_hidden_agreement_message":
        payload["assistant_message"] = "Please confirm."
    elif scenario == "alignment_incomplete_agreement_checklist":
        payload["readiness_checklist"]["workflow_shape"] = False
        payload["assistant_message"] = "请确认这份还没完成 workflow 判断的协议。"
    elif scenario == "alignment_incomplete_tradeoff_checklist":
        payload["readiness_checklist"]["judgment_tradeoffs"] = False
        payload["assistant_message"] = "请确认这份还没完成判断取舍的协议。"
    elif scenario == "alignment_unresolved_open_questions":
        payload["readiness_evidence"]["open_questions"] = "Need the user to decide whether browser evidence or test output should persuade GateKeeper."
        payload["assistant_message"] = "Please confirm; the evidence choice is still open."
    elif scenario == "alignment_english_agreement_for_chinese_user":
        payload = alignment_agreement_response()
        payload["assistant_message"] = "Please confirm."
    elif scenario == "alignment_survive_chat_loop_fit_readiness_evidence":
        payload["readiness_evidence"]["loop_fit"] = (
            "This is not one Agent pass plus human review because the judgment should survive one chat "
            "as run evidence, export, reuse, and audit material for future rounds."
        )
    _apply_alignment_agreement_readiness_override(payload, scenario)
    return payload


def _apply_alignment_agreement_readiness_override(payload: dict, scenario: str) -> None:
    if scenario == "alignment_missing_evidence_bucket_readiness_evidence":
        payload["readiness_evidence"]["evidence_preferences"] = (
            "The strongest evidence is direct command output, tests, or concrete artifacts created by the project."
        )
    elif scenario == "alignment_governance_markers_listed_without_responsibilities":
        payload["readiness_evidence"]["workdir_facts"] = (
            "Workdir Snapshot observed project-local governance markers: AGENTS.md, design/README.md, design/, and tests/. "
            "Their contents are unknown, but the Loop must route them into runtime responsibilities."
        )
