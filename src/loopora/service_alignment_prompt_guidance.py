from __future__ import annotations

from dataclasses import dataclass


ALIGNMENT_PROMPT_BUNDLE_GUIDANCE_STAGES = frozenset({"confirmed", "compiling", "ready_review"})


@dataclass(frozen=True)
class AlignmentPromptGuidanceProjection:
    example_profile: str
    bundle_contract: str
    feedback_improvement: str


def alignment_prompt_guidance_profile(session: dict, *, mode: str) -> str:
    if mode == "repair":
        return "bundle"
    stage = str(session.get("alignment_stage", "") or "clarifying").strip().lower()
    if stage in ALIGNMENT_PROMPT_BUNDLE_GUIDANCE_STAGES:
        return "bundle"
    if stage == "agreement_ready":
        return "agreement"
    return "clarifying"


def alignment_prompt_guidance_projection(
    session: dict,
    *,
    mode: str,
    bundle_contract: str,
    feedback_improvement: str,
) -> AlignmentPromptGuidanceProjection:
    profile = alignment_prompt_guidance_profile(session, mode=mode)
    agreement = session.get("working_agreement")
    agreement_mode = str(agreement.get("mode") or "") if isinstance(agreement, dict) else ""
    return AlignmentPromptGuidanceProjection(
        example_profile=profile,
        bundle_contract=bundle_contract if profile == "bundle" else "",
        feedback_improvement=feedback_improvement if agreement_mode == "improvement" else "",
    )
