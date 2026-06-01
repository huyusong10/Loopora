from __future__ import annotations

from dataclasses import dataclass

from loopora.service_alignment_agreement_confirmation_terms import (
    AGREEMENT_ADJUSTMENT_TOKENS,
    AGREEMENT_CONFIRMATION_TOKENS,
    AGREEMENT_NO_CHANGE_MARKERS,
)
from loopora.service_alignment_decision_options import agreement_confirmation_decision_options


@dataclass(frozen=True)
class AlignmentUserMessageStagePlan:
    update_fields: dict
    event_type: str = ""
    event_payload: dict | None = None


@dataclass(frozen=True)
class AlignmentAgreementReadyStagePlan:
    update_fields: dict
    output_updates: dict
    event_type: str
    event_payload: dict


def alignment_agreement_working_agreement(output: dict, *, captured_at: str) -> dict:
    checklist = output.get("readiness_checklist")
    normalized_checklist = dict(checklist) if isinstance(checklist, dict) else {}
    normalized_checklist["explicit_confirmation"] = False
    readiness_evidence = output.get("readiness_evidence")
    return {
        "summary": str(output.get("agreement_summary", "") or "").strip(),
        "readiness_checklist": normalized_checklist,
        "readiness_evidence": readiness_evidence if isinstance(readiness_evidence, dict) else {},
        "captured_at": captured_at,
        "confirmed_at": "",
        "confirmation_message": "",
    }


def alignment_merge_improvement_context(previous: object, working_agreement: dict) -> dict:
    if not isinstance(previous, dict) or previous.get("mode") != "improvement":
        return working_agreement
    merged = dict(working_agreement)
    for key in ("mode", "source", "seed_bundle_metadata"):
        if key in previous and key not in merged:
            merged[key] = previous[key]
    return merged


def alignment_visible_agreement_message(working_agreement: dict, *, prefers_chinese: bool) -> str:
    evidence = working_agreement.get("readiness_evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    summary = alignment_agreement_text_snippet(working_agreement.get("summary"), limit=360)
    values = {
        key: alignment_agreement_text_snippet(evidence.get(key), limit=280)
        for key in (
            "loop_fit",
            "task_scope",
            "success_surface",
            "fake_done_risks",
            "evidence_preferences",
            "execution_strategy",
            "residual_risk_policy",
            "judgment_tradeoffs",
            "local_governance",
            "role_posture",
            "workflow_shape",
            "workdir_facts",
        )
    }
    if prefers_chinese:
        return "\n".join(
            [
                "请先确认这份工作协议。确认后我再生成 Loop 方案；如果任一判断不对，请直接指出要改哪一项。",
                "",
                f"摘要：{summary}",
                f"为什么用 Loopora：{values['loop_fit']}",
                f"任务范围：{values['task_scope']}",
                f"成功面：{values['success_surface']}",
                f"假完成风险：{values['fake_done_risks']}",
                f"证据偏好：{values['evidence_preferences']}",
                f"执行策略：{values['execution_strategy']}",
                f"残余风险：{values['residual_risk_policy']}",
                f"判断取舍：{values['judgment_tradeoffs']}",
                f"本地治理：{values['local_governance']}",
                f"角色姿态：{values['role_posture']}",
                f"运行流程形状：{values['workflow_shape']}",
                f"项目事实：{values['workdir_facts']}",
            ]
        )
    return "\n".join(
        [
            "Please confirm this working agreement. After confirmation I will generate the Loop plan; if any judgment is wrong, name the item to adjust.",
            "",
            f"Summary: {summary}",
            f"Loopora fit: {values['loop_fit']}",
            f"Task scope: {values['task_scope']}",
            f"Success surface: {values['success_surface']}",
            f"Fake-done risks: {values['fake_done_risks']}",
            f"Evidence preferences: {values['evidence_preferences']}",
            f"Execution strategy: {values['execution_strategy']}",
            f"Residual risk: {values['residual_risk_policy']}",
            f"Judgment tradeoffs: {values['judgment_tradeoffs']}",
            f"Local governance: {values['local_governance']}",
            f"Role posture: {values['role_posture']}",
            f"Run-flow shape: {values['workflow_shape']}",
            f"Project facts: {values['workdir_facts']}",
        ]
    )


def alignment_agreement_text_snippet(value: object, *, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def alignment_agreement_ready_stage_plan(
    working_agreement: dict,
    *,
    assistant_message: str,
    prefers_chinese: bool,
) -> AlignmentAgreementReadyStagePlan:
    return AlignmentAgreementReadyStagePlan(
        update_fields={
            "alignment_stage": "agreement_ready",
            "working_agreement": working_agreement,
        },
        output_updates={
            "assistant_message": assistant_message,
            "needs_user_input": True,
            "bundle_yaml": "",
            "decision_options": agreement_confirmation_decision_options(prefers_chinese=prefers_chinese),
        },
        event_type="alignment_agreement_ready",
        event_payload={
            "alignment_stage": "agreement_ready",
            "working_agreement": working_agreement,
        },
    )


def alignment_user_message_stage_plan(
    session: dict,
    message: str,
    *,
    captured_at: str,
    confirmed_stages: set[str],
) -> AlignmentUserMessageStagePlan:
    stage = str(session.get("alignment_stage", "") or "clarifying")
    status = str(session.get("status", "") or "")
    if stage == "agreement_ready":
        agreement = dict(session.get("working_agreement") or {})
        checklist = dict(agreement.get("readiness_checklist") or {})
        if alignment_message_confirms_agreement(message):
            checklist["explicit_confirmation"] = True
            agreement["readiness_checklist"] = checklist
            agreement["confirmed_at"] = captured_at
            agreement["confirmation_message"] = message
            return AlignmentUserMessageStagePlan(
                update_fields={"alignment_stage": "confirmed", "working_agreement": agreement},
                event_type="alignment_agreement_confirmed",
                event_payload={"alignment_stage": "confirmed"},
            )
        checklist["explicit_confirmation"] = False
        agreement["readiness_checklist"] = checklist
        agreement["confirmed_at"] = ""
        agreement["confirmation_message"] = ""
        return AlignmentUserMessageStagePlan(
            update_fields={"alignment_stage": "clarifying", "working_agreement": agreement},
            event_type="alignment_agreement_reopened",
            event_payload={"alignment_stage": "clarifying"},
        )
    if status == "ready":
        agreement = dict(session.get("working_agreement") or {})
        ready_review = dict(agreement.get("ready_review") or {})
        ready_review["feedback"] = message
        ready_review["requested_at"] = captured_at
        ready_review["source_status"] = status
        agreement["ready_review"] = ready_review
        return AlignmentUserMessageStagePlan(
            update_fields={"alignment_stage": "ready_review", "working_agreement": agreement},
            event_type="alignment_ready_review_started",
            event_payload={
                "alignment_stage": "ready_review",
                "feedback": message,
                "bundle_path": session.get("bundle_path", ""),
            },
        )
    if status in {"imported", "running_loop"}:
        return AlignmentUserMessageStagePlan(
            update_fields={
                "alignment_stage": "clarifying",
                "working_agreement": session.get("working_agreement") or {},
            },
        )
    if status == "failed" and stage not in confirmed_stages:
        return AlignmentUserMessageStagePlan(update_fields={"alignment_stage": "clarifying"})
    return AlignmentUserMessageStagePlan(update_fields={})


def alignment_message_confirms_agreement(message: str) -> bool:
    normalized = str(message or "").strip().lower()
    if not normalized:
        return False
    if normalized in {"no", "nope"}:
        return False
    negative_scan = normalized
    for no_change_marker in AGREEMENT_NO_CHANGE_MARKERS:
        negative_scan = negative_scan.replace(no_change_marker, "")
    if any(token in negative_scan for token in AGREEMENT_ADJUSTMENT_TOKENS):
        return False
    return any(token in normalized for token in AGREEMENT_CONFIRMATION_TOKENS)


def alignment_agreement_readiness_checklist_issues(checklist: object, *, readiness_keys: list[str]) -> list[str]:
    if not isinstance(checklist, dict):
        return ["readiness_checklist"]
    return [key for key in readiness_keys if key != "explicit_confirmation" and checklist.get(key) is not True]
