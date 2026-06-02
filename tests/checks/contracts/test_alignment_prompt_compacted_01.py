from __future__ import annotations

# Merged from test_alignment_prompt_build_context.py
from pathlib import Path

from loopora.service_alignment_prompting import AlignmentPromptBuildContext, build_alignment_prompt


def test_build_alignment_prompt_collects_context_inputs_before_rendering(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.yml"
    workdir = tmp_path / "project"
    calls: list[tuple[str, str]] = []

    context = AlignmentPromptBuildContext(
        current_bundle_text=lambda path: calls.append(("bundle", str(path)))
        or "version: 1\nmetadata:\n  name: Context Bundle\n",
        workdir_snapshot=lambda path: calls.append(("workdir", str(path))) or "Top-level entries (1 shown):\n- src/",
        user_language_hint=lambda session: calls.append(("language", str(session["id"]))) or "Use Chinese.",
    )

    prompt = build_alignment_prompt(
        context,
        {
            "id": "align_prompt",
            "bundle_path": str(bundle_path),
            "workdir": str(workdir),
            "alignment_stage": "clarifying",
            "transcript": [],
            "working_agreement": {},
        },
        mode="normal",
    )

    assert calls == [
        ("bundle", str(bundle_path)),
        ("workdir", str(workdir)),
        ("language", "align_prompt"),
    ]
    assert "Context Bundle" in prompt
    assert "Top-level entries (1 shown):" in prompt
    assert "Use Chinese." in prompt

# Merged from test_alignment_prompt_source_context.py

from loopora.service_alignment_prompting import (
    alignment_current_bundle_prompt_text,
    alignment_improvement_context_text,
)


def test_alignment_improvement_context_text_renders_selected_spec_and_redacts_sources() -> None:
    context = alignment_improvement_context_text(
        {
            "working_agreement": {
                "mode": "selected_source",
                "source": {
                    "source_type": "spec_file",
                    "spec_path": "/tmp/spec.md",
                    "reason": "start_from_workdir_spec",
                    "artifact_paths": {"spec": "/tmp/spec.md"},
                    "spec_markdown": "Use Authorization: Bearer PROMPT_SPEC_TOKEN_SECRET",
                },
            }
        }
    )

    assert "Selected Loopora Source Context" in context
    assert "PROMPT_SPEC_TOKEN_SECRET" not in context
    assert "<secret omitted>" in context
    assert "Bundle Improvement Context" not in context


def test_alignment_improvement_context_text_renders_run_evidence_context_with_redaction() -> None:
    context = alignment_improvement_context_text(
        {
            "working_agreement": {
                "mode": "improvement",
                "source": {
                    "source_type": "run",
                    "source_run_id": "run_1",
                    "run_status": "succeeded",
                    "source_completion_mode": "all_checks_pass",
                    "evidence_summary": [{"claim": "Cookie: sid=PROMPT_COOKIE_SECRET"}],
                    "coverage_summary": {"summary": "Authorization: Bearer PROMPT_COVERAGE_SECRET"},
                    "judgment_contract": {"done_when": ["proof"]},
                    "task_verdict": {"summary": "insufficient"},
                    "gatekeeper_verdict": {"summary": "needs evidence"},
                },
            }
        }
    )

    assert "Selected Loopora Source Context" in context
    assert "Bundle Improvement Context" in context
    assert "PROMPT_COOKIE_SECRET" not in context
    assert "PROMPT_COVERAGE_SECRET" not in context
    assert "<secret omitted>" in context


def test_alignment_current_bundle_prompt_text_reads_and_redacts_bundle(tmp_path: Path) -> None:
    bundle_path = tmp_path / "bundle.yml"
    bundle_path.write_text(
        "version: 1\nmetadata:\n  name: Authorization: Bearer CURRENT_BUNDLE_TOKEN_SECRET\n",
        encoding="utf-8",
    )

    text = alignment_current_bundle_prompt_text(bundle_path)

    assert "CURRENT_BUNDLE_TOKEN_SECRET" not in text
    assert "<secret omitted>" in text
    assert alignment_current_bundle_prompt_text(tmp_path / "missing.yml") == ""

# Merged from test_alignment_prompt_stage_policy.py
import pytest

from loopora.service_alignment_prompting import alignment_stage_policy_text
from loopora.service_types import LooporaError


def test_alignment_stage_policy_text_selects_repair_and_ready_sections() -> None:
    compiler_gates = "\n".join(
        [
            "## Common",
            "Common policy.",
            "## Repair",
            "Repair policy.",
            "## Ready Review",
            "Ready policy.",
            "## Clarifying",
            "Clarifying policy.",
            "## Confirmed Agreement",
            "Confirmed policy.",
        ]
    )

    repair_policy = alignment_stage_policy_text(
        {"alignment_stage": "ready_review"}, mode="repair", compiler_gates=compiler_gates
    )
    ready_policy = alignment_stage_policy_text(
        {"alignment_stage": "ready_review"}, mode="generate", compiler_gates=compiler_gates
    )
    confirmed_policy = alignment_stage_policy_text(
        {"alignment_stage": "confirmed"}, mode="generate", compiler_gates=compiler_gates
    )

    assert repair_policy == "Common policy.\n\nRepair policy."
    assert ready_policy == "Common policy.\n\nReady policy."
    assert confirmed_policy == "Common policy.\n\nConfirmed policy."


def test_alignment_stage_policy_text_fails_closed_when_policy_section_is_missing() -> None:
    with pytest.raises(LooporaError, match="Common"):
        alignment_stage_policy_text({"alignment_stage": "clarifying"}, mode="generate", compiler_gates="## Clarifying\nPolicy")

# Merged from test_alignment_prompt_template_helpers.py

from loopora.service_alignment_prompting import alignment_markdown_h2_sections, render_alignment_template


def test_render_alignment_template_replaces_known_values_and_rejects_unknowns() -> None:
    assert render_alignment_template("Hello {{ name }}", {"name": "Loopora"}) == "Hello Loopora"

    with pytest.raises(LooporaError, match="unknown value"):
        render_alignment_template("Hello {{ missing }}", {})


def test_alignment_markdown_h2_sections_collects_section_bodies() -> None:
    assert alignment_markdown_h2_sections("# Title\n\n## Common\nA\n## Repair\nB\n") == {
        "Common": "A",
        "Repair": "B",
    }

# Merged from test_alignment_prompt_text_rendering.py
from loopora.service_alignment_prompting import build_alignment_prompt_text


def test_build_alignment_prompt_text_renders_repair_context_and_redacts_session_values() -> None:
    prompt = build_alignment_prompt_text(
        {
            "bundle_path": "/tmp/bundle.yml",
            "workdir": "/tmp/project",
            "executor_kind": "codex",
            "executor_mode": "preset",
            "command_args_text": "--token PROMPT_COMMAND_TOKEN_SECRET",
            "alignment_stage": "ready_review",
            "transcript": [{"role": "user", "content": "Cookie: sid=PROMPT_TRANSCRIPT_COOKIE_SECRET"}],
            "working_agreement": {"summary": "Authorization: Bearer PROMPT_AGREEMENT_TOKEN_SECRET"},
        },
        mode="repair",
        workdir_snapshot="Top-level entries (0 shown):",
        user_language_hint="Use Chinese.",
        validation_error="bundle field missing",
        invalid_yaml="version: 1",
    )

    assert "bundle field missing" in prompt
    assert "Use Chinese." in prompt
    assert "PROMPT_COMMAND_TOKEN_SECRET" not in prompt
    assert "PROMPT_TRANSCRIPT_COOKIE_SECRET" not in prompt
    assert "PROMPT_AGREEMENT_TOKEN_SECRET" not in prompt
    assert "<secret omitted>" in prompt


def test_build_alignment_prompt_text_renders_current_bundle_context() -> None:
    prompt = build_alignment_prompt_text(
        {
            "bundle_path": "/tmp/bundle.yml",
            "workdir": "/tmp/project",
            "alignment_stage": "clarifying",
            "transcript": [],
            "working_agreement": {},
        },
        mode="normal",
        current_bundle="version: 1\nmetadata:\n  name: Current\n",
    )

    assert "Current Bundle" in prompt
    assert "metadata:" in prompt
