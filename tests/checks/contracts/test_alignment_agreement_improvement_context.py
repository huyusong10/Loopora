from __future__ import annotations

from loopora.service_alignment_agreement_stage import alignment_merge_improvement_context


def test_alignment_merge_improvement_context_preserves_source_metadata() -> None:
    previous = {
        "mode": "improvement",
        "source": {"source_bundle_id": "bundle_source"},
        "seed_bundle_metadata": {"name": "Source"},
    }
    working_agreement = {
        "summary": "New improvement agreement.",
        "source": {"source_bundle_id": "explicit_new_source"},
    }

    merged = alignment_merge_improvement_context(previous, working_agreement)

    assert merged == {
        "summary": "New improvement agreement.",
        "mode": "improvement",
        "source": {"source_bundle_id": "explicit_new_source"},
        "seed_bundle_metadata": {"name": "Source"},
    }
    assert working_agreement == {
        "summary": "New improvement agreement.",
        "source": {"source_bundle_id": "explicit_new_source"},
    }


def test_alignment_merge_improvement_context_ignores_non_improvement_previous_agreement() -> None:
    working_agreement = {"summary": "Fresh agreement."}

    assert (
        alignment_merge_improvement_context(
            {"mode": "standard", "source": {"id": "ignored"}},
            working_agreement,
        )
        is working_agreement
    )
    assert alignment_merge_improvement_context(["bad"], working_agreement) is working_agreement
