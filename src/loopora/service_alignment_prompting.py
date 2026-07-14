from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.event_redaction import redact_sensitive_text
from loopora.service_alignment_language import alignment_user_language_hint
from loopora.service_alignment_prompt_examples import (
    alignment_example_core_headings as alignment_example_core_headings,
)
from loopora.service_alignment_prompt_examples import (
    alignment_example_topic_keywords as alignment_example_topic_keywords,
)
from loopora.service_alignment_prompt_examples import (
    alignment_relevant_examples_prompt_text as alignment_relevant_examples_prompt_text,
)
from loopora.service_alignment_prompt_guidance import (
    AlignmentPromptGuidanceProjection as AlignmentPromptGuidanceProjection,
)
from loopora.service_alignment_prompt_guidance import (
    alignment_prompt_guidance_profile as alignment_prompt_guidance_profile,
)
from loopora.service_alignment_prompt_guidance import (
    alignment_prompt_guidance_projection as alignment_prompt_guidance_projection,
)
from loopora.service_alignment_prompt_source_projection import (
    alignment_current_bundle_prompt_text as alignment_current_bundle_prompt_text,
)
from loopora.service_alignment_prompt_source_projection import (
    alignment_improvement_context_text as alignment_improvement_context_text,
)
from loopora.service_alignment_prompt_templates import (
    ALIGNMENT_PROMPT_CONFIRMED_STAGES as ALIGNMENT_PROMPT_CONFIRMED_STAGES,
)
from loopora.service_alignment_prompt_templates import (
    alignment_markdown_h2_sections as alignment_markdown_h2_sections,
)
from loopora.service_alignment_prompt_templates import (
    alignment_stage_policy_text as alignment_stage_policy_text,
)
from loopora.service_alignment_prompt_templates import (
    render_alignment_template as render_alignment_template,
)
from loopora.service_alignment_prompt_transcript import (
    alignment_prompt_transcript_projection as alignment_prompt_transcript_projection,
)
from loopora.service_alignment_source_context import redact_alignment_model_context_value
from loopora.service_alignment_workdir_snapshot import alignment_workdir_snapshot


@dataclass(frozen=True)
class AlignmentPromptBuildContext:
    current_bundle_text: Callable[[Path], str] = alignment_current_bundle_prompt_text
    workdir_snapshot: Callable[[Path], str] = alignment_workdir_snapshot
    user_language_hint: Callable[[dict], str] = alignment_user_language_hint


def build_alignment_prompt(
    context: AlignmentPromptBuildContext,
    session: dict,
    *,
    mode: str,
    validation_error: str = "",
    invalid_yaml: str = "",
) -> str:
    return build_alignment_prompt_text(
        session,
        mode=mode,
        current_bundle=context.current_bundle_text(Path(session["bundle_path"])),
        workdir_snapshot=context.workdir_snapshot(Path(session["workdir"])),
        user_language_hint=context.user_language_hint(session),
        validation_error=validation_error,
        invalid_yaml=invalid_yaml,
    )


def build_alignment_prompt_text(  # noqa: PLR0913 - prompt rendering exposes explicit externally collected context.
    session: dict,
    *,
    mode: str,
    current_bundle: str = "",
    workdir_snapshot: str = "",
    user_language_hint: str = "",
    validation_error: str = "",
    invalid_yaml: str = "",
) -> str:
    guidance = load_alignment_guidance_assets()
    prompt_transcript = alignment_prompt_transcript_projection(session.get("transcript"))
    transcript_text = redact_sensitive_text(json.dumps(prompt_transcript, ensure_ascii=False, indent=2))
    prompt_working_agreement = redact_alignment_model_context_value(session.get("working_agreement") or {})
    working_agreement_text = redact_sensitive_text(json.dumps(prompt_working_agreement or {}, ensure_ascii=False, indent=2))
    alignment_stage = str(session.get("alignment_stage", "") or "clarifying")
    improvement_context = alignment_improvement_context_text(session)
    stage_policy = alignment_stage_policy_text(
        session,
        mode=mode,
        compiler_gates=guidance.compiler_gates,
    )
    guidance_projection = alignment_prompt_guidance_projection(
        session,
        mode=mode,
        bundle_contract=guidance.bundle_contract,
        feedback_improvement=guidance.feedback_improvement,
    )
    example_context_text = "\n".join(
        part
        for part in (
            transcript_text,
            working_agreement_text,
            improvement_context,
            current_bundle,
            validation_error,
            invalid_yaml,
        )
        if part
    )
    examples_text = alignment_relevant_examples_prompt_text(
        guidance.examples,
        context_text=example_context_text,
        example_selection=guidance.example_selection,
        profile=guidance_projection.example_profile,
    )
    session_context = ""
    if mode == "repair":
        session_context = render_alignment_template(
            guidance.repair_input_template,
            {
                "validation_error": validation_error,
                "invalid_yaml": invalid_yaml,
            },
        )
    elif current_bundle:
        session_context = render_alignment_template(
            guidance.current_bundle_template,
            {"current_bundle": current_bundle},
        )

    return render_alignment_template(
        guidance.system_prompt_template,
        {
            "bundle_path": session["bundle_path"],
            "workdir": session["workdir"],
            "executor_kind": session.get("executor_kind", "codex"),
            "executor_mode": session.get("executor_mode", "preset"),
            "command_cli": session.get("command_cli", ""),
            "command_args_text": redact_sensitive_text(str(session.get("command_args_text", "") or "")),
            "model": session.get("model", ""),
            "reasoning_effort": session.get("reasoning_effort", ""),
            "workdir_snapshot": workdir_snapshot,
            "alignment_stage": alignment_stage,
            "working_agreement_json": working_agreement_text,
            "improvement_context": improvement_context,
            "stage_policy": stage_policy,
            "product_primer": guidance.product_primer,
            "compiler_policy": guidance.compiler_policy,
            "alignment_playbook": guidance.alignment_playbook,
            "quality_rubric": guidance.quality_rubric,
            "bundle_contract": guidance_projection.bundle_contract,
            "examples": examples_text,
            "feedback_improvement": guidance_projection.feedback_improvement,
            "session_transcript_json": transcript_text,
            "session_context": session_context,
            "user_language_hint": user_language_hint,
        },
    )
