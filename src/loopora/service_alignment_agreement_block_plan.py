from __future__ import annotations

from dataclasses import dataclass

from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.service_alignment_decision_option_catalog import (
    default_alignment_decision_options,
    not_fit_alignment_decision_options,
)
from loopora.service_alignment_agreement_block_messages import (
    alignment_block_message,
    alignment_not_fit_block_message,
)


@dataclass(frozen=True)
class AlignmentAgreementBlockCandidate:
    issues: list[str]
    event_type: str
    fallback_message: str


@dataclass(frozen=True)
class AlignmentAgreementBlockPlan:
    event_type: str
    event_payload: dict
    output_updates: dict


def alignment_agreement_block_plan(
    candidates: list[AlignmentAgreementBlockCandidate],
    *,
    prefers_chinese: bool,
    display_language: str = "",
    not_fit_source_text: str = "",
) -> AlignmentAgreementBlockPlan | None:
    for candidate in candidates:
        missing = list(candidate.issues)
        if not missing:
            continue
        use_not_fit = alignment_block_should_offer_skip_loop(missing, not_fit_source_text)
        return AlignmentAgreementBlockPlan(
            event_type=candidate.event_type,
            event_payload={"alignment_stage": "clarifying", "missing": missing},
            output_updates={
                "alignment_phase": "clarifying",
                "agreement_summary": "",
                "bundle_yaml": "",
                "needs_user_input": True,
                "alignment_missing_items": missing,
                "assistant_message": (
                    alignment_not_fit_block_message(
                        prefers_chinese=prefers_chinese,
                        display_language=display_language,
                    )
                    if use_not_fit
                    else alignment_block_message(
                        prefers_chinese=prefers_chinese,
                        display_language=display_language,
                        event_type=candidate.event_type,
                        missing=missing,
                        fallback_zh=candidate.fallback_message,
                    )
                ),
                "decision_options": (
                    not_fit_alignment_decision_options(
                        prefers_chinese=prefers_chinese,
                        display_language=display_language,
                    )
                    if use_not_fit
                    else default_alignment_decision_options(
                        prefers_chinese=prefers_chinese,
                        display_language=display_language,
                    )
                ),
            },
        )
    return None


def alignment_block_should_offer_skip_loop(missing: list[str], source_text: str) -> bool:
    return "loop_fit" in set(missing) and text_mentions_loop_fit_contradiction(source_text)
