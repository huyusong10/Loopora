from __future__ import annotations

import re
from collections.abc import Mapping

from loopora.alignment_semantics import semantic_antipattern_match_is_negated
from loopora.alignment_guidance import load_alignment_guidance_assets


ALIGNMENT_EXAMPLE_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def alignment_example_core_headings(
    example_selection: Mapping[str, object] | None = None,
    *,
    profile: str = "",
) -> tuple[str, ...]:
    selection = example_selection if example_selection is not None else load_alignment_guidance_assets().example_selection
    profile_config = _alignment_example_profile_config(selection, profile=profile)
    headings = profile_config.get("core_headings") if profile_config else selection.get("core_headings")
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
    profile: str = "",
) -> str:
    preamble, sections = _alignment_markdown_h2_section_blocks(examples)
    if not sections:
        return str(examples or "").strip()

    normalized_context = str(context_text or "").lower()
    selected_headings: list[str] = []
    core_headings = alignment_example_core_headings(example_selection, profile=profile)
    topic_keywords = alignment_example_topic_keywords(example_selection)

    def add_heading(heading: str) -> None:
        if heading in sections and heading not in selected_headings:
            selected_headings.append(heading)

    for heading in core_headings:
        add_heading(heading)

    if _alignment_example_profile_includes_topic_matches(example_selection, profile=profile):
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
    return any(not _alignment_context_example_keyword_match_is_negated(normalized_context, match.start()) for match in re.finditer(pattern, normalized_context))


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


def _alignment_example_profile_config(
    example_selection: Mapping[str, object] | None,
    *,
    profile: str,
) -> Mapping[str, object]:
    profiles = example_selection.get("profiles") if isinstance(example_selection, Mapping) else None
    if not profile or not isinstance(profiles, Mapping):
        return {}
    config = profiles.get(profile)
    return config if isinstance(config, Mapping) else {}


def _alignment_example_profile_includes_topic_matches(
    example_selection: Mapping[str, object] | None,
    *,
    profile: str,
) -> bool:
    config = _alignment_example_profile_config(example_selection, profile=profile)
    return config.get("include_topic_matches") is not False
