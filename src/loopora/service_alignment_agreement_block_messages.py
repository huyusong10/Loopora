from __future__ import annotations

from loopora.service_alignment_agreement_missing_items import (
    alignment_missing_item_label,
    alignment_missing_items_followup_question,
)


def alignment_not_fit_block_message(*, prefers_chinese: bool, display_language: str = "") -> str:
    if prefers_chinese:
        return (
            "这看起来更像一次性任务、直接回答或已有检查足够裁决的工作，不适合先编排成 Loop。"
            "除非后续轮次会产生一次 Agent 执行没有的新证据、handoff 或 GateKeeper 判断，否则建议先不生成 Loop。"
        )
    if str(display_language or "").strip().lower() == "es":
        return (
            "Esto parece una tarea puntual, respuesta directa, o trabajo ya cubierto por checks existentes; "
            "no conviene componerlo como Loop todavía. Salvo que rondas posteriores produzcan evidencia, handoffs "
            "o juicio de GateKeeper que una sola pasada no produciría, recomiendo omitir el Loop."
        )
    return (
        "This looks like one-off work, a direct answer, or work already decided by existing checks, "
        "so it is not suitable to compose as a Loop yet. Unless later rounds would create new evidence, "
        "handoffs, or GateKeeper judgment that one Agent pass would not, skip Loop generation for now."
    )


def alignment_block_message(
    *,
    prefers_chinese: bool,
    display_language: str = "",
    event_type: str,
    missing: list[str],
    fallback_zh: str,
) -> str:
    labels = ", ".join(
        alignment_missing_item_label(
            item,
            prefers_chinese=prefers_chinese,
            display_language=display_language,
        )
        for item in missing
    )
    followup = alignment_missing_items_followup_question(
        missing,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    if prefers_chinese:
        return _alignment_block_message_with_followup(
            fallback_zh.format(missing=labels),
            followup=followup,
            event_type=event_type,
            prefers_chinese=True,
            display_language=display_language,
        )
    message = alignment_block_message_base(
        event_type=event_type,
        labels=labels,
        fallback=fallback_zh,
        display_language=display_language,
    )
    return _alignment_block_message_with_followup(
        message,
        followup=followup,
        event_type=event_type,
        prefers_chinese=False,
        display_language=display_language,
    )


def alignment_block_message_base(*, event_type: str, labels: str, fallback: str, display_language: str = "") -> str:
    if str(display_language or "").strip().lower() == "es":
        return alignment_block_message_base_es(event_type=event_type, labels=labels)
    return alignment_block_message_base_en(event_type=event_type, labels=labels, fallback=fallback)


def alignment_block_message_base_en(*, event_type: str, labels: str, fallback: str) -> str:
    if event_type == "alignment_checklist_incomplete":
        return f"I can't prepare the confirmation agreement yet; these readiness checks are incomplete: {labels}."
    if event_type == "alignment_evidence_incomplete":
        return f"I can't prepare the confirmation agreement yet; this readiness evidence is not specific enough: {labels}."
    if event_type == "alignment_improvement_incomplete":
        return f"I can't prepare the improvement agreement yet; these source-based improvement judgments are not specific enough: {labels}."
    if event_type == "alignment_language_mismatch":
        return (
            "I can't prepare the confirmation agreement yet; these user-facing agreement fields need "
            f"the user's language: {labels}. Please rewrite those judgments."
        )
    return fallback.format(missing=labels)


def alignment_block_message_base_es(*, event_type: str, labels: str) -> str:
    if event_type == "alignment_checklist_incomplete":
        return f"Todavía no puedo preparar el acuerdo de confirmación; estas revisiones de preparación están incompletas: {labels}."
    if event_type == "alignment_evidence_incomplete":
        return f"Todavía no puedo preparar el acuerdo de confirmación; esta evidencia de preparación no es suficientemente específica: {labels}."
    if event_type == "alignment_improvement_incomplete":
        return f"Todavía no puedo preparar el acuerdo de mejora; estos juicios basados en la fuente no son suficientemente específicos: {labels}."
    if event_type == "alignment_language_mismatch":
        return f"Todavía no puedo preparar el acuerdo de confirmación; estos campos visibles necesitan el idioma del usuario: {labels}. Reescribe esos juicios."
    return f"Todavía no puedo preparar el acuerdo de confirmación; faltan estos juicios: {labels}."


def _alignment_block_message_with_followup(
    message: str,
    *,
    followup: str,
    event_type: str,
    prefers_chinese: bool,
    display_language: str = "",
) -> str:
    if not followup or event_type == "alignment_language_mismatch":
        return message
    if prefers_chinese:
        suffix = f"下一步请回答：{followup}"
    elif str(display_language or "").strip().lower() == "es":
        suffix = f"Responde: {followup}"
    else:
        suffix = f"Please answer: {followup}"
    return f"{message} {suffix}"
