from __future__ import annotations

from loopora.specs import compile_markdown_spec, resolve_role_note

BUILDER_NOTE = "Move the workspace toward a verifiable state with focused edits."
SPECIFIED_SAMPLE_CHECK_COUNT = 2


def test_compile_markdown_spec_extracts_sections(sample_spec_text: str) -> None:
    compiled = compile_markdown_spec(sample_spec_text)
    assert compiled["goal"] == "Ship the requested behavior."
    assert compiled["check_mode"] == "specified"
    assert len(compiled["checks"]) == SPECIFIED_SAMPLE_CHECK_COUNT
    assert compiled["checks"][0]["id"] == "check_001"
    assert compiled["checks"][1]["expect"] == "The edge path stays safe and understandable."
    assert compiled["constraints"] == "- Keep changes focused."
    assert compiled["success_surface"] == [
        "The result remains easy for the next role to verify.",
        "The surrounding contract stays clear enough to revise safely.",
    ]
    assert compiled["fake_done_states"] == [
        "A happy-path-only result that leaves the edge path unverifiable.",
    ]
    assert compiled["evidence_preferences"] == [
        "Prefer structured run artifacts and reproducible checks over role self-report.",
    ]
    assert _coverage_target_ids(compiled) == [
        "done_when.check_001",
        "done_when.check_002",
        "success_surface.surface_001",
        "success_surface.surface_002",
        "fake_done.risk_001",
        "evidence_preference.pref_001",
        "gatekeeper.finish",
    ]
    assert compiled["coverage_targets"][0]["required"] is True
    assert compiled["coverage_targets"][2]["required"] is False
    assert "unverifiable completion should fail closed" in compiled["residual_risk"]
    assert compiled["role_notes"]["builder"] == BUILDER_NOTE


def test_compile_markdown_spec_allows_missing_checks_for_exploration(exploratory_spec_text: str) -> None:
    compiled = compile_markdown_spec(exploratory_spec_text)
    assert compiled["goal"] == "Build a rough prototype that proves the main interaction is promising."
    assert compiled["check_mode"] == "auto_generated"
    assert compiled["checks"] == []
    assert _coverage_target_ids(compiled) == ["gatekeeper.finish"]


def test_compile_markdown_spec_ignores_html_comments_inside_sections() -> None:
    compiled = compile_markdown_spec(
        """# Task

<!-- temporary note -->
Ship the requested behavior.

# Guardrails

<!-- keep files -->
- Preserve existing files.
"""
    )
    assert compiled["goal"] == "Ship the requested behavior."
    assert compiled["constraints"] == "- Preserve existing files."


def test_resolve_role_note_matches_role_name_and_archetype(sample_spec_text: str) -> None:
    compiled = compile_markdown_spec(sample_spec_text)
    assert resolve_role_note(compiled, role_name="Builder") == BUILDER_NOTE
    assert resolve_role_note(compiled, role_name="Release Builder", archetype="builder") == BUILDER_NOTE


def test_compile_markdown_spec_does_not_promote_nested_bullets_to_contract_items() -> None:
    compiled = compile_markdown_spec(
        """# Task

Ship the requested behavior.

# Done When

- The primary flow works end to end.
  - This nested note explains the evidence path but is not a separate check.

# Fake Done

- The UI looks done but the behavior is not verified.
  - This nested note is not a second fake-done risk.

# Evidence Preferences

- Prefer reproducible project commands.
  - This nested note is not a second evidence preference.
"""
    )

    assert [check["expect"] for check in compiled["checks"]] == ["The primary flow works end to end."]
    assert compiled["fake_done_states"] == ["The UI looks done but the behavior is not verified."]
    assert compiled["evidence_preferences"] == ["Prefer reproducible project commands."]
    assert _coverage_target_ids(compiled) == [
        "done_when.check_001",
        "fake_done.risk_001",
        "evidence_preference.pref_001",
        "gatekeeper.finish",
    ]


def _coverage_target_ids(compiled: dict) -> list[str]:
    return [item["id"] for item in compiled["coverage_targets"]]
