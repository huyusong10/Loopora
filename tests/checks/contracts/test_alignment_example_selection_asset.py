from __future__ import annotations

from pathlib import Path

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.service_alignment_prompting import (
    alignment_example_core_headings,
    alignment_example_topic_keywords,
    alignment_markdown_h2_sections,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_example_selection_policy_lives_in_asset_and_matches_examples() -> None:
    assets = load_alignment_guidance_assets()
    sections = alignment_markdown_h2_sections(assets.examples)
    core_headings = alignment_example_core_headings(assets.example_selection)
    topic_keywords = alignment_example_topic_keywords(assets.example_selection)

    assert "Long-chain RAG grounding workflow example" in topic_keywords
    assert "retrieval acl" in topic_keywords["Long-chain RAG grounding workflow example"]
    assert "Workdir governance marker example" in core_headings

    missing = [heading for heading in (*core_headings, *topic_keywords.keys()) if heading not in sections]
    assert missing == []

    prompting_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_prompting.py").read_text(
        encoding="utf-8"
    )
    assert "ALIGNMENT_EXAMPLE_TOPIC_KEYWORDS" not in prompting_source
    assert "Support impersonation break-glass example" not in prompting_source
