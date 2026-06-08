from __future__ import annotations

from loopora.alignment_readiness_rules import alignment_governance_marker_responsibilities_present
from loopora.service_alignment_traceability_projection import (
    alignment_bundle_agreement_projection_text,
    alignment_bundle_runtime_responsibility_projection_text,
    alignment_governance_marker_responsibility_issues,
    alignment_session_user_task_text,
    alignment_traceability_term_is_present,
    normalize_alignment_traceability_text,
)


def test_alignment_bundle_traceability_projection_texts_expose_only_runnable_surfaces() -> None:
    bundle = {
        "collaboration_summary": "Refund risk must reach GateKeeper.",
        "spec": {"markdown": "# Spec\n\n## Role Notes\nBuilder reads AGENTS.md before editing."},
        "workflow": {
            "collaboration_intent": "Builder then GateKeeper.",
            "steps": [
                {
                    "role": "builder",
                    "inputs": {"iteration_memory": "previous gaps"},
                    "action_policy": {"can_finish_run": False},
                    "control": {"handoff": "gatekeeper"},
                    "private": "not stable",
                },
                "ignore malformed step",
            ],
            "controls": [{"after": "builder", "then": "gatekeeper"}],
        },
        "role_definitions": [
            {
                "key": "builder",
                "name": "Builder",
                "description": "Builds refund controls.",
                "prompt_markdown": "Read AGENTS.md and cite evidence.",
                "posture_notes": "Do not treat process success as proof.",
            },
            "ignore malformed role",
        ],
    }

    agreement_text = alignment_bundle_agreement_projection_text(bundle)
    runtime_text = alignment_bundle_runtime_responsibility_projection_text(bundle)
    normalized = normalize_alignment_traceability_text("  Refund\n\nRisk  ")

    assert "Refund risk must reach GateKeeper." in agreement_text
    assert "Builds refund controls." in agreement_text
    assert '"inputs": {"iteration_memory": "previous gaps"}' in agreement_text
    assert "Read AGENTS.md and cite evidence." in runtime_text
    assert '"private"' not in agreement_text
    assert normalized == "refund risk"
    assert alignment_traceability_term_is_present("refund", normalized_bundle_text=normalize_alignment_traceability_text(agreement_text))
    assert alignment_traceability_term_is_present("AGENTS.md", normalized_bundle_text=normalize_alignment_traceability_text(runtime_text))
    assert not alignment_traceability_term_is_present("fund", normalized_bundle_text=normalize_alignment_traceability_text(agreement_text))


def test_alignment_session_user_task_text_projects_first_user_messages() -> None:
    session = {
        "transcript": [
            {"role": "system", "content": "ignored"},
            {"role": "user", "content": "  First task.  "},
            {"role": "assistant", "content": "ignored"},
            {"role": "user", "content": ""},
            {"role": "user", "content": "Second task."},
            {"role": "user", "content": "Third task."},
            {"role": "user", "content": "Fourth task."},
            {"role": "user", "content": "Fifth task."},
            "ignore malformed",
        ]
    }

    assert alignment_session_user_task_text(session) == "First task.\nSecond task.\nThird task.\nFourth task."
    assert alignment_session_user_task_text({"transcript": "bad"}) == ""


def test_alignment_governance_marker_responsibility_issues_require_runtime_ownership() -> None:
    evidence = {
        "local_governance": "AGENTS.md, design/README.md, design/, and tests/ are visible governance markers.",
    }
    disconnected_runtime = normalize_alignment_traceability_text(
        "AGENTS.md, design/README.md, design/, and tests/. "
        + ("Neutral context keeps marker lists separate from role responsibilities. " * 10)
        + "Builder reads task notes. "
        "Inspector checks the result. GateKeeper blocks weak proof."
    )
    connected_runtime = normalize_alignment_traceability_text(
        "Builder reads AGENTS.md and design/README.md before editing. "
        "Inspector verifies design/ and tests/ obligations against the result. "
        "GateKeeper treats skipped AGENTS.md or tests/ validation as weak, unproven, or blocking."
    )

    assert alignment_governance_marker_responsibility_issues({}, normalized_runtime_text=disconnected_runtime) == []
    assert alignment_governance_marker_responsibility_issues(evidence, normalized_runtime_text=disconnected_runtime) == [
        "alignment bundle must convert project-local governance markers into Builder reading, "
        "Inspector or Custom verification, and GateKeeper gating responsibilities"
    ]
    assert alignment_governance_marker_responsibilities_present(connected_runtime)
    assert alignment_governance_marker_responsibility_issues(evidence, normalized_runtime_text=connected_runtime) == []


def test_alignment_governance_marker_responsibilities_accept_locate_design_language() -> None:
    runtime_text = normalize_alignment_traceability_text(
        "Builder must locate design/README.md and identify the relevant design/ boundary before changing work. "
        "Inspector verifies design/tests/schema obligations against the result. "
        "GateKeeper treats skipped project-local design/tests/schema validation as Weak, Unproven, or Blocking."
    )

    assert alignment_governance_marker_responsibilities_present(runtime_text)
