from __future__ import annotations

from loopora.agent_native_coverage_summary import (
    coverage_classification_note,
    coverage_gap_summaries,
    evidence_scope_items,
    required_coverage_summary,
)


def test_agent_native_required_coverage_summary_labels_partial_and_target_counts() -> None:
    summary = required_coverage_summary(
        {
            "status": "partial",
            "covered_check_count": 2,
            "missing_check_count": 1,
            "target_count": 4,
            "covered_target_count": 1,
            "weak_target_count": 1,
            "missing_target_count": 1,
            "blocked_target_count": 1,
        }
    )

    assert summary == "partial evidence; required checks 2 covered / 1 missing, 1/4 targets covered / 1 weak / 1 missing / 1 blocked"


def test_agent_native_coverage_classification_note_tracks_unclassified_supporting_evidence() -> None:
    note = coverage_classification_note(
        {
            "known_evidence_count": 3,
            "required_coverage": {
                "target_count": 2,
                "covered_target_count": 1,
                "top_gaps": [{"target_id": "done_when.audit"}],
            },
            "known_evidence_refs": [
                {
                    "id": "ev_old",
                    "gatekeeper_support": "supporting",
                    "coverage_target_ids": ["done_when.audit"],
                },
                {
                    "id": "ev_new",
                    "gatekeeper_support": "supporting",
                    "coverage_target_ids": [],
                },
            ],
        }
    )

    assert note.startswith("ev_new is citable")
    assert "coverage_results" in note


def test_agent_native_coverage_classification_note_suppresses_gatekeeper_finish_only_gap() -> None:
    note = coverage_classification_note(
        {
            "known_evidence_ids": ["ev_builder"],
            "required_coverage": {
                "target_count": 1,
                "covered_target_count": 1,
                "missing_check_count": 0,
                "top_gaps": [{"target_id": "gatekeeper.finish"}],
            },
            "known_evidence_refs": [{"id": "ev_builder", "gatekeeper_support": "supporting"}],
        }
    )

    assert note == ""


def test_agent_native_coverage_gap_summaries_are_bounded_and_semantic() -> None:
    summaries = coverage_gap_summaries(
        [
            {
                "target_id": "done_when.audit",
                "status": "blocked",
                "source_section": "done_when",
                "reason": "Audit evidence is missing.",
                "text": "Prove audit replay.",
                "evidence_refs": ["ev_blocker", "ev_support"],
            },
            {"id": "done_when.extra", "status": "missing", "text": "Extra gap"},
        ],
        limit=1,
    )

    assert summaries == [
        {
            "target_id": "done_when.audit",
            "status": "blocked",
            "source_section": "done_when",
            "reason": "Audit evidence is missing.",
            "text": "Prove audit replay.",
            "evidence_refs": ["ev_blocker", "ev_support"],
        }
    ]
    assert evidence_scope_items([" a ", "", 12]) == ["a", "12"]
