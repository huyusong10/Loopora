from __future__ import annotations

from pathlib import Path

from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.service_alignment_prompting import (
    alignment_current_bundle_prompt_text,
    alignment_example_core_headings,
    alignment_example_topic_keywords,
    alignment_improvement_context_text,
    alignment_markdown_h2_sections,
    alignment_prompt_guidance_projection,
    alignment_prompt_transcript_projection,
    alignment_stage_policy_text,
    render_alignment_template,
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
    for profile in ("clarifying", "agreement", "bundle"):
        profile_headings = alignment_example_core_headings(assets.example_selection, profile=profile)
        assert profile_headings
        assert all(heading in sections for heading in profile_headings)

    example_source = (REPO_ROOT / "src" / "loopora" / "service_alignment_prompt_examples.py").read_text(encoding="utf-8")
    assert "ALIGNMENT_EXAMPLE_TOPIC_KEYWORDS" not in example_source
    assert "Support impersonation break-glass example" not in example_source


def test_alignment_prompt_transcript_projection_has_dedicated_model_context_boundary() -> None:
    design_source = (REPO_ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert alignment_prompt_transcript_projection.__module__ == "loopora.service_alignment_prompt_transcript"
    assert "service_alignment_prompt_transcript.py" in design_source
    assert "bounded model-visible transcript projection" in design_source


def test_alignment_prompt_guidance_has_dedicated_stage_projection_boundary() -> None:
    design_source = (REPO_ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert alignment_prompt_guidance_projection.__module__ == "loopora.service_alignment_prompt_guidance"
    assert "service_alignment_prompt_guidance.py" in design_source
    assert "stage-aware bundle/improvement guidance selection" in design_source


def test_alignment_prompt_helpers_have_dedicated_template_example_and_source_boundaries() -> None:
    design_source = (REPO_ROOT / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert alignment_example_core_headings.__module__ == "loopora.service_alignment_prompt_examples"
    assert alignment_example_topic_keywords.__module__ == "loopora.service_alignment_prompt_examples"
    assert render_alignment_template.__module__ == "loopora.service_alignment_prompt_templates"
    assert alignment_markdown_h2_sections.__module__ == "loopora.service_alignment_prompt_templates"
    assert alignment_stage_policy_text.__module__ == "loopora.service_alignment_prompt_templates"
    assert alignment_improvement_context_text.__module__ == "loopora.service_alignment_prompt_source_projection"
    assert alignment_current_bundle_prompt_text.__module__ == "loopora.service_alignment_prompt_source_projection"
    for filename in (
        "service_alignment_prompt_examples.py",
        "service_alignment_prompt_templates.py",
        "service_alignment_prompt_source_projection.py",
        "service_alignment_prompting.py",
    ):
        assert filename in design_source
