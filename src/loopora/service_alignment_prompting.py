from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from loopora.alignment_semantics import semantic_antipattern_match_is_negated
from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.bundles import BundleError, read_bundle_file_text
from loopora.event_redaction import redact_sensitive_text
from loopora.service_alignment_language import alignment_user_language_hint
from loopora.service_alignment_workdir_snapshot import alignment_workdir_snapshot
from loopora.service_types import LooporaError


ALIGNMENT_PROMPT_CONFIRMED_STAGES = frozenset({"confirmed", "compiling", "ready_review"})
ALIGNMENT_TEMPLATE_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")
ALIGNMENT_EXAMPLE_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


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


def _alignment_markdown_h2_section_blocks(markdown_text: str) -> tuple[str, dict[str, str]]:
    text = str(markdown_text or "")
    matches = list(ALIGNMENT_EXAMPLE_HEADING_RE.finditer(text))
    if not matches:
        return text.strip(), {}
    preamble = text[: matches[0].start()].strip()
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[heading] = text[match.start() : next_start].strip()
    return preamble, sections


def _alignment_context_has_example_keyword(normalized_context: str, keyword: str) -> bool:
    normalized_keyword = str(keyword or "").lower().strip()
    if not normalized_keyword:
        return False
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*", normalized_keyword):
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])"
    else:
        pattern = re.escape(normalized_keyword)
    return any(
        not _alignment_context_example_keyword_match_is_negated(normalized_context, match.start())
        for match in re.finditer(pattern, normalized_context)
    )


def _alignment_context_example_keyword_match_is_negated(normalized_context: str, start: int) -> bool:
    if semantic_antipattern_match_is_negated(normalized_context, start):
        return True
    sentence_prefix = re.split(r"[.!?。！？;；\n]", normalized_context[max(0, start - 96) : start])[-1]
    if re.search(r"\bnot\s+only\b", sentence_prefix, re.IGNORECASE):
        return False
    return bool(
        re.search(r"\b(?:not|never|no)\b(?:(?!\bbut\b).){0,80}(?:\bor\b|/|,)\s*$", sentence_prefix, re.IGNORECASE)
        or re.search(r"(?:不是|并非|不要|不能|不需要).{0,80}(?:或|和|、|，)\s*$", sentence_prefix)
    )


def alignment_example_core_headings(example_selection: Mapping[str, object] | None = None) -> tuple[str, ...]:
    selection = example_selection if example_selection is not None else load_alignment_guidance_assets().example_selection
    headings = selection.get("core_headings") if isinstance(selection, Mapping) else ()
    if not isinstance(headings, list | tuple):
        return ()
    return tuple(str(heading).strip() for heading in headings if str(heading).strip())


def alignment_example_topic_keywords(example_selection: Mapping[str, object] | None = None) -> dict[str, tuple[str, ...]]:
    selection = example_selection if example_selection is not None else load_alignment_guidance_assets().example_selection
    topics = selection.get("topic_keywords") if isinstance(selection, Mapping) else {}
    if not isinstance(topics, Mapping):
        return {}
    normalized: dict[str, tuple[str, ...]] = {}
    for heading, raw_keywords in topics.items():
        if not isinstance(raw_keywords, list | tuple):
            continue
        keywords = tuple(str(keyword).strip() for keyword in raw_keywords if str(keyword).strip())
        if keywords:
            normalized[str(heading).strip()] = keywords
    return normalized


def alignment_relevant_examples_prompt_text(
    examples: str,
    *,
    context_text: str = "",
    example_selection: Mapping[str, object] | None = None,
) -> str:
    preamble, sections = _alignment_markdown_h2_section_blocks(examples)
    if not sections:
        return str(examples or "").strip()

    normalized_context = str(context_text or "").lower()
    selected_headings: list[str] = []
    core_headings = alignment_example_core_headings(example_selection)
    topic_keywords = alignment_example_topic_keywords(example_selection)

    def add_heading(heading: str) -> None:
        if heading in sections and heading not in selected_headings:
            selected_headings.append(heading)

    for heading in core_headings:
        add_heading(heading)

    for heading in sections:
        if heading in core_headings:
            continue
        keywords = topic_keywords.get(heading, ())
        if any(_alignment_context_has_example_keyword(normalized_context, keyword) for keyword in keywords):
            add_heading(heading)

    selected_blocks = [sections[heading] for heading in selected_headings]
    if preamble:
        return "\n\n".join([preamble, *selected_blocks]).strip()
    return "\n\n".join(selected_blocks).strip()


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


def alignment_improvement_context_text(session: dict) -> str:
    agreement = session.get("working_agreement") if isinstance(session.get("working_agreement"), dict) else {}
    mode = str(agreement.get("mode") or "")
    if mode not in {"improvement", "selected_source"}:
        return ""
    source = agreement.get("source") if isinstance(agreement.get("source"), dict) else {}
    artifact_paths_text = redact_sensitive_text(json.dumps(source.get("artifact_paths") or {}, ensure_ascii=False, indent=2))
    transcript_summary_text = redact_sensitive_text(json.dumps(source.get("transcript_summary") or [], ensure_ascii=False, indent=2))
    spec_markdown = redact_sensitive_text(str(source.get("spec_markdown") or ""))
    guidance = load_alignment_guidance_assets()
    selected_spec_markdown_block = ""
    if spec_markdown:
        selected_spec_markdown_block = render_alignment_template(
            guidance.selected_spec_markdown_template,
            {"spec_markdown": spec_markdown},
        )
    source_values = {
        "source_type": source.get("source_type", ""),
        "source_alignment_session_id": source.get("source_alignment_session_id", ""),
        "source_bundle_id": source.get("source_bundle_id", ""),
        "source_loop_id": source.get("source_loop_id", ""),
        "source_run_id": source.get("source_run_id", ""),
        "spec_path": source.get("spec_path", ""),
        "reason": source.get("reason", ""),
        "artifact_paths_json": artifact_paths_text,
        "transcript_summary_json": transcript_summary_text,
        "selected_spec_markdown_block": selected_spec_markdown_block,
    }
    selected_context = render_alignment_template(guidance.selected_source_context_template, source_values)
    if mode == "selected_source":
        return selected_context
    evidence_items = source.get("evidence_summary") if isinstance(source.get("evidence_summary"), list) else []
    evidence_text = redact_sensitive_text(json.dumps(evidence_items[:8], ensure_ascii=False, indent=2))
    coverage_text = redact_sensitive_text(json.dumps(source.get("coverage_summary") or {}, ensure_ascii=False, indent=2))
    judgment_contract_text = redact_sensitive_text(json.dumps(source.get("judgment_contract") or {}, ensure_ascii=False, indent=2))
    task_verdict_text = redact_sensitive_text(json.dumps(source.get("task_verdict") or {}, ensure_ascii=False, indent=2))
    verdict_text = redact_sensitive_text(json.dumps(source.get("gatekeeper_verdict") or {}, ensure_ascii=False, indent=2))
    improvement_context = render_alignment_template(
        guidance.bundle_improvement_context_template,
        {
            **source_values,
            "run_status": source.get("run_status", ""),
            "source_completion_mode": source.get("source_completion_mode", ""),
            "judgment_contract_json": judgment_contract_text,
            "coverage_summary_json": coverage_text,
            "task_verdict_json": task_verdict_text,
            "evidence_summary_json": evidence_text,
            "gatekeeper_verdict_json": verdict_text,
        },
    )
    return selected_context + "\n\n" + improvement_context


def alignment_current_bundle_prompt_text(bundle_path: Path) -> str:
    path = Path(bundle_path)
    if not path.exists():
        return ""
    try:
        return redact_sensitive_text(read_bundle_file_text(path))
    except (BundleError, OSError) as exc:
        return f"Current bundle file could not be read: {exc}"


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
    transcript_text = redact_sensitive_text(json.dumps(session.get("transcript") or [], ensure_ascii=False, indent=2))
    working_agreement_text = redact_sensitive_text(json.dumps(session.get("working_agreement") or {}, ensure_ascii=False, indent=2))
    alignment_stage = str(session.get("alignment_stage", "") or "clarifying")
    improvement_context = alignment_improvement_context_text(session)
    stage_policy = alignment_stage_policy_text(session, mode=mode, compiler_gates=guidance.compiler_gates)
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
            {
                "current_bundle": current_bundle,
            },
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
            "bundle_contract": guidance.bundle_contract,
            "examples": examples_text,
            "feedback_improvement": guidance.feedback_improvement,
            "session_transcript_json": transcript_text,
            "session_context": session_context,
            "user_language_hint": user_language_hint,
        },
    )
