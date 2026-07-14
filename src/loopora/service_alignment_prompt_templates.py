from __future__ import annotations

import re

from loopora.service_types import LooporaError


ALIGNMENT_PROMPT_CONFIRMED_STAGES = frozenset({"confirmed", "compiling", "ready_review"})
ALIGNMENT_TEMPLATE_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def render_alignment_template(template: str, values: dict[str, object]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise LooporaError(f"alignment prompt template references unknown value: {key}")
        return str(values[key])

    return ALIGNMENT_TEMPLATE_PLACEHOLDER_RE.sub(replace, template).strip()


def alignment_markdown_h2_sections(markdown_text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current_heading = ""
    for line in str(markdown_text or "").splitlines():
        if line.startswith("## "):
            current_heading = line.removeprefix("## ").strip()
            sections.setdefault(current_heading, [])
            continue
        if current_heading:
            sections[current_heading].append(line)
    return {heading: "\n".join(lines).strip() for heading, lines in sections.items()}


def alignment_stage_policy_text(
    session: dict,
    *,
    mode: str,
    compiler_gates: str,
    confirmed_stages: set[str] | frozenset[str] = ALIGNMENT_PROMPT_CONFIRMED_STAGES,
) -> str:
    stage = str(session.get("alignment_stage", "") or "clarifying")
    sections = alignment_markdown_h2_sections(compiler_gates)
    if mode == "repair":
        section_name = "Repair"
    elif stage == "agreement_ready":
        section_name = "Waiting For Confirmation"
    elif stage == "ready_review":
        section_name = "Ready Review"
    elif stage in confirmed_stages:
        section_name = "Confirmed Agreement"
    else:
        section_name = "Clarifying"
    try:
        common = sections["Common"]
        stage_policy = sections[section_name]
    except KeyError as exc:
        raise LooporaError(f"Loop compiler policy asset is missing section: {exc.args[0]}") from exc
    return "\n\n".join(part for part in (common, stage_policy) if part).strip()
