from __future__ import annotations

from dataclasses import dataclass

from loopora.service_alignment_decision_option_catalog import agreement_confirmation_decision_options


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


def alignment_visible_agreement_message(
    working_agreement: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
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
    if str(display_language or "").strip().lower() == "es":
        return "\n".join(
            [
                "Confirma primero este acuerdo de trabajo. Después generaré el plan Loop; si algún juicio está mal, nombra el punto que quieres ajustar.",
                "",
                f"Resumen: {summary}",
                f"Encaje con Loopora: {values['loop_fit']}",
                f"Alcance de tarea: {values['task_scope']}",
                f"Superficie de éxito: {values['success_surface']}",
                f"Riesgos de falso terminado: {values['fake_done_risks']}",
                f"Preferencias de evidencia: {values['evidence_preferences']}",
                f"Estrategia de ejecución: {values['execution_strategy']}",
                f"Riesgo residual: {values['residual_risk_policy']}",
                f"Tradeoffs de juicio: {values['judgment_tradeoffs']}",
                f"Gobernanza local: {values['local_governance']}",
                f"Postura de roles: {values['role_posture']}",
                f"Forma del flujo de ejecución: {values['workflow_shape']}",
                f"Hechos del proyecto: {values['workdir_facts']}",
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
    display_language: str = "",
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
            "decision_options": agreement_confirmation_decision_options(
                prefers_chinese=prefers_chinese,
                display_language=display_language,
            ),
        },
        event_type="alignment_agreement_ready",
        event_payload={
            "alignment_stage": "agreement_ready",
            "working_agreement": working_agreement,
        },
    )
