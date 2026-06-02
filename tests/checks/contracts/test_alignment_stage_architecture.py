from __future__ import annotations

from pathlib import Path

from loopora.alignment_readiness_rules import alignment_governance_marker_responsibilities_present
from loopora.service_alignment_stage import (
    AlignmentAgreementBlockCandidate,
    alignment_bundle_workdir_fact_issues,
    alignment_clarifying_stage_plan,
    alignment_improvement_bundle_issues,
    alignment_output_message_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_stage_bundle_issue_selectors_have_dedicated_boundary() -> None:
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert alignment_bundle_workdir_fact_issues.__module__ == "loopora.service_alignment_stage_bundle_issues"
    assert alignment_improvement_bundle_issues.__module__ == "loopora.service_alignment_stage_bundle_issues"
    assert alignment_output_message_plan.__module__ == "loopora.service_alignment_stage_messages"
    assert AlignmentAgreementBlockCandidate.__module__ == "loopora.service_alignment_stage_messages"
    assert alignment_clarifying_stage_plan.__module__ == "loopora.service_alignment_stage_messages"
    assert alignment_governance_marker_responsibilities_present.__module__ == "loopora.alignment_readiness_governance"
    assert "service_alignment_stage_bundle_issues.py" in design_source
    assert "service_alignment_stage_messages.py" in design_source
    assert "alignment_readiness_governance.py" in design_source
