from __future__ import annotations

from dataclasses import dataclass

from loopora.service_alignment_clarifying_questions import alignment_clarifying_question_issues
from loopora.service_alignment_decision_option_catalog import default_alignment_decision_options
from loopora.service_alignment_decision_option_normalization import alignment_needs_user_input
from loopora.service_alignment_language import alignment_assistant_message_language_issue
from loopora.service_alignment_agreement_block_messages import (
    alignment_block_message as alignment_block_message,
    alignment_block_message_base as alignment_block_message_base,
    alignment_block_message_base_en as alignment_block_message_base_en,
    alignment_block_message_base_es as alignment_block_message_base_es,
    alignment_not_fit_block_message as alignment_not_fit_block_message,
)
from loopora.service_alignment_agreement_block_plan import (
    AlignmentAgreementBlockCandidate as AlignmentAgreementBlockCandidate,
    AlignmentAgreementBlockPlan as AlignmentAgreementBlockPlan,
    alignment_agreement_block_plan as alignment_agreement_block_plan,
    alignment_block_should_offer_skip_loop as alignment_block_should_offer_skip_loop,
)
from loopora.service_alignment_agreement_missing_items import (
    alignment_missing_item_followup_question as alignment_missing_item_followup_question,
    alignment_missing_item_label as alignment_missing_item_label,
    alignment_missing_items_followup_question as alignment_missing_items_followup_question,
)


@dataclass(frozen=True)
class AlignmentOutputMessagePlan:
    assistant_message: str
    bundle_yaml: str
    missing_items: list[str] | None
    has_bundle_for_options: bool
    event_type: str = ""
    event_payload: dict | None = None
    force_needs_user_input: bool = False
    use_default_decision_options: bool = False


@dataclass(frozen=True)
class AlignmentClarifyingStagePlan:
    update_fields: dict
    output_updates: dict
    event_type: str = ""
    event_payload: dict | None = None


def alignment_output_message_plan(  # noqa: PLR0913 - output planning keeps stage, missing-item, and language gates explicit.
    output: dict,
    *,
    stage_error: str,
    stage_missing_items: list[str] | None = None,
    missing_items: list[str] | None,
    prefers_chinese: bool,
    display_language: str = "",
) -> AlignmentOutputMessagePlan:
    assistant_message = str(output.get("assistant_message", "") or "").strip()
    bundle_yaml = str(output.get("bundle_yaml", "") or "").strip()
    if stage_error:
        event_payload = {"status": "waiting_user", "error": stage_error}
        if stage_missing_items:
            event_payload["missing"] = list(stage_missing_items)
        return AlignmentOutputMessagePlan(
            assistant_message=stage_error,
            bundle_yaml="",
            missing_items=None,
            has_bundle_for_options=False,
            event_type="alignment_stage_blocked",
            event_payload=event_payload,
            force_needs_user_input=True,
            use_default_decision_options=True,
        )
    if assistant_message and alignment_assistant_message_language_issue(
        assistant_message,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    ):
        return AlignmentOutputMessagePlan(
            assistant_message=alignment_fallback_assistant_message(
                has_bundle=bool(bundle_yaml),
                needs_user_input=alignment_needs_user_input(output),
                display_language=display_language,
            ),
            bundle_yaml=bundle_yaml,
            missing_items=missing_items,
            has_bundle_for_options=bool(bundle_yaml),
            event_type="alignment_language_mismatch",
            event_payload={"missing": ["assistant_message"], "surface": "assistant_message"},
            use_default_decision_options=True,
        )
    return AlignmentOutputMessagePlan(
        assistant_message=assistant_message,
        bundle_yaml=bundle_yaml,
        missing_items=missing_items,
        has_bundle_for_options=bool(bundle_yaml),
    )


def alignment_fallback_assistant_message(
    *,
    has_bundle: bool,
    needs_user_input: bool,
    display_language: str = "",
) -> str:
    if str(display_language or "").strip().lower() == "es":
        if has_bundle:
            return "Preparé un bundle de Loopora importable."
        if needs_user_input:
            return "Necesito seguir alineando en tu idioma; confirma primero qué riesgo importa más: falso terminado sin evidencia o avanzar demasiado lento."
        return "Necesito seguir alineando en tu idioma antes de continuar."
    if has_bundle:
        return "已整理成一个可导入的 Loopora bundle。"
    if needs_user_input:
        return "我需要继续用中文对齐；请先确认一个会改变 Loop 形状的点：这次更怕结果看起来完成但证据不足，还是推进太慢？"
    return "我需要继续用中文对齐后再继续。"


def alignment_clarifying_reframe_message(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return "我先给一个推荐判断：默认应该优先阻断“看起来完成但证据不足”的结果，这样后续运行不会靠漂亮叙事过关。你可以直接选推荐，也可以改成更偏速度的方向。"
    if str(display_language or "").strip().lower() == "es":
        return (
            "Mi recomendación inicial es bloquear resultados que parecen terminados pero no tienen evidencia, "
            "para que la ejecución no pase por una historia pulida. Puedes elegir esa recomendación o priorizar velocidad."
        )
    return (
        "My recommended default is to block results that look done but lack evidence, so the run cannot "
        "pass on a polished story alone. You can choose that recommendation or switch toward speed."
    )


def alignment_clarifying_stage_plan(
    output: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> AlignmentClarifyingStagePlan:
    question_issues = alignment_clarifying_question_issues(output)
    if not question_issues:
        return AlignmentClarifyingStagePlan(update_fields={"alignment_stage": "clarifying"}, output_updates={})
    return AlignmentClarifyingStagePlan(
        update_fields={"alignment_stage": "clarifying"},
        output_updates={
            "assistant_message": alignment_clarifying_reframe_message(
                prefers_chinese=prefers_chinese,
                display_language=display_language,
            ),
            "decision_options": default_alignment_decision_options(
                prefers_chinese=prefers_chinese,
                display_language=display_language,
            ),
            "needs_user_input": True,
            "bundle_yaml": "",
        },
        event_type="alignment_question_reframed",
        event_payload={"alignment_stage": "clarifying", "issues": question_issues},
    )
