from __future__ import annotations

from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.service_alignment_decision_option_catalog import (
    agreement_confirmation_decision_options,
    default_alignment_decision_options,
    not_fit_alignment_decision_options,
)
from loopora.service_alignment_decision_option_normalization import (
    alignment_decision_options_are_visible,
    alignment_needs_user_input,
    normalize_alignment_decision_options,
)


def visible_alignment_decision_options(
    output: dict,
    *,
    has_bundle: bool,
    prefers_chinese: bool,
    display_language: str = "",
) -> list[dict]:
    if has_bundle:
        return []
    phase = str(output.get("alignment_phase", "") or "").strip().lower()
    status = str(output.get("status", "") or "").strip().lower()
    if not alignment_needs_user_input(output) and phase != "blocked" and status != "blocked":
        return []
    if alignment_output_is_not_fit(output) or phase == "blocked" or status == "blocked":
        return not_fit_alignment_decision_options(
            prefers_chinese=prefers_chinese,
            display_language=display_language,
        )
    options = normalize_alignment_decision_options(output.get("decision_options"))
    if alignment_decision_options_are_visible(options):
        return options
    if phase == "agreement":
        return agreement_confirmation_decision_options(
            prefers_chinese=prefers_chinese,
            display_language=display_language,
        )
    return default_alignment_decision_options(
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )


def alignment_output_is_not_fit(output: dict) -> bool:
    checklist = output.get("readiness_checklist")
    if not isinstance(checklist, dict) or checklist.get("loop_fit") is not False:
        return False
    text_parts: list[str] = [
        str(output.get("assistant_message") or ""),
        str(output.get("review_reply_preview") or ""),
        str(output.get("review_status") or ""),
        str(output.get("review_recommended_action") or ""),
    ]
    evidence = output.get("readiness_evidence")
    if isinstance(evidence, dict):
        text_parts.extend(
            str(evidence.get(key) or "")
            for key in (
                "loop_fit",
                "workflow_shape",
                "execution_strategy",
                "residual_risk_policy",
                "open_questions",
            )
        )
    raw_options = output.get("decision_options")
    if isinstance(raw_options, list):
        for option in raw_options:
            if isinstance(option, dict):
                text_parts.extend(str(option.get(key) or "") for key in ("id", "label", "description", "user_reply"))
    return text_mentions_loop_fit_contradiction(" ".join(text_parts))
