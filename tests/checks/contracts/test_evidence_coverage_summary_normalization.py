from __future__ import annotations

from loopora.evidence_coverage_summary import summarize_evidence_coverage_projection


NORMALIZED_MISSING_CHECK_COUNT = 1
NORMALIZED_MISSING_TARGET_COUNT = 2
NORMALIZED_TARGET_COUNT = 4


def test_coverage_summary_requires_integer_counts() -> None:
    summary = summarize_evidence_coverage_projection(
        {
            "status": "partial",
            "evidence_count": True,
            "check_count": "2",
            "covered_check_count": 1.5,
            "missing_check_count": NORMALIZED_MISSING_CHECK_COUNT,
            "target_count": NORMALIZED_TARGET_COUNT,
            "covered_target_count": "1",
            "weak_target_count": True,
            "missing_target_count": NORMALIZED_MISSING_TARGET_COUNT,
            "blocked_target_count": 0,
            "artifact_ref_count": "3",
            "residual_risk_count": True,
        }
    )

    assert summary["evidence_count"] == 0
    assert summary["check_count"] == 0
    assert summary["covered_check_count"] == 0
    assert summary["missing_check_count"] == NORMALIZED_MISSING_CHECK_COUNT
    assert summary["target_count"] == NORMALIZED_TARGET_COUNT
    assert summary["covered_target_count"] == 0
    assert summary["weak_target_count"] == 0
    assert summary["missing_target_count"] == NORMALIZED_MISSING_TARGET_COUNT
    assert summary["blocked_target_count"] == 0
    assert summary["artifact_ref_count"] == 0
    assert summary["residual_risk_count"] == 0


def test_coverage_summary_drops_malformed_collection_shapes() -> None:
    summary = summarize_evidence_coverage_projection(
        {
            "status": "partial",
            "summary": "not a mapping",
            "covered_check_ids": "check_001",
            "missing_check_ids": ["check_002", 7, True],
            "top_gaps": [
                "not a gap",
                {"target_id": "done_when.check_001", "status": "missing"},
            ],
            "evidence_kind_counts": ["builder", "gatekeeper"],
            "risk_signals": "manual review needed",
            "latest_gatekeeper": "not a mapping",
        }
    )

    assert summary["summary"] == {}
    assert summary["covered_check_ids"] == []
    assert summary["missing_check_ids"] == ["check_002"]
    assert summary["top_gaps"] == [{"target_id": "done_when.check_001", "status": "missing"}]
    assert summary["evidence_kind_counts"] == {}
    assert summary["risk_signals"] == []
    assert summary["latest_gatekeeper"] == {}
