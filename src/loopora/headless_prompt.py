from __future__ import annotations

from dataclasses import dataclass

from loopora.context_flow import (
    _combine_role_guidance,
    output_contract_prompt,
    render_artifact_refs,
    render_continuation_section,
    render_evidence_section,
    render_handoff_list_section,
    render_handoff_section,
    render_iteration_section,
    render_previous_iteration_summary,
    render_role_note_section,
    render_run_contract_section,
    system_prompt_prefix,
)
from loopora.specs import resolve_role_note


@dataclass(frozen=True)
class HeadlessPromptRequest:
    role: dict
    prompt_label: str
    prompt_body: str
    step_instruction_context: dict
    compiled_spec: dict


def build_headless_prompt(request: HeadlessPromptRequest) -> str:
    role = request.role
    prompt_label = request.prompt_label
    prompt_body = request.prompt_body
    step_context = request.step_instruction_context
    compiled_spec = request.compiled_spec
    role_note = resolve_role_note(
        compiled_spec,
        role_name=str(role.get("name") or ""),
        archetype=str(role.get("archetype") or ""),
    )
    role_posture = str(role.get("posture_notes", "") or "").strip()
    role_guidance = _combine_role_guidance(role_note, role_posture)
    sections = [
        f"You are {role['name']} inside Loopora.",
        system_prompt_prefix(role["archetype"]),
        output_contract_prompt(role["archetype"]),
        prompt_body.strip(),
        render_run_contract_section(step_context["contract"], compiled_spec),
        render_continuation_section(step_context.get("continuation") or {}),
        render_role_note_section(role_guidance),
        render_iteration_section(step_context),
        render_handoff_section(
            "Immediate upstream handoff",
            step_context["upstream"]["immediate_previous_step"],
            empty_text="No previous step has completed in this iteration yet.",
        ),
        render_handoff_list_section(
            "Completed steps in this iteration",
            step_context["upstream"]["completed_steps_this_iteration"],
            empty_text="No earlier steps have completed in this iteration yet.",
        ),
        render_handoff_section(
            "Previous iteration · same step",
            step_context["upstream"]["previous_iteration_same_step"],
            empty_text="This step has no previous-iteration handoff yet.",
        ),
        render_handoff_section(
            "Previous iteration · same role",
            step_context["upstream"]["previous_iteration_same_role"],
            empty_text="This role has no previous-iteration handoff yet.",
        ),
        render_previous_iteration_summary(step_context["upstream"]["previous_iteration_summary"]),
        render_evidence_section(step_context.get("evidence") or {}),
        render_artifact_refs(step_context["artifacts"]),
        f"Prompt template: {prompt_label}",
    ]
    return "\n\n".join(section for section in sections if str(section).strip()).strip()
