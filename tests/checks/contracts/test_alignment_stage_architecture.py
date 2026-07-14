from __future__ import annotations

from strategy_source_architecture_test_support import design_boundary_source

from loopora.alignment_readiness_rules import alignment_governance_marker_responsibilities_present
from loopora.service_alignment_agreement_stage import (
    alignment_agreement_readiness_checklist_issues,
    alignment_message_confirms_agreement,
    alignment_user_message_stage_plan,
    alignment_visible_agreement_message,
)
from loopora.service_alignment_decision_options import (
    default_alignment_decision_options,
    normalize_alignment_decision_options,
    visible_alignment_decision_options,
)
from loopora.service_alignment_stage import (
    AlignmentAgreementBlockCandidate,
    alignment_agreement_block_plan,
    alignment_block_message,
    alignment_bundle_workdir_fact_issues,
    alignment_clarifying_stage_plan,
    alignment_improvement_bundle_issues,
    alignment_missing_item_label,
    alignment_output_message_plan,
)


def test_alignment_stage_bundle_issue_selectors_have_dedicated_boundary() -> None:
    design_source = design_boundary_source()

    assert alignment_bundle_workdir_fact_issues.__module__ == "loopora.service_alignment_stage_bundle_issues"
    assert alignment_improvement_bundle_issues.__module__ == "loopora.service_alignment_stage_bundle_issues"
    assert alignment_output_message_plan.__module__ == "loopora.service_alignment_stage_messages"
    assert alignment_clarifying_stage_plan.__module__ == "loopora.service_alignment_stage_messages"
    assert alignment_governance_marker_responsibilities_present.__module__ == "loopora.alignment_readiness_governance"
    assert "service_alignment_stage_bundle_issues.py" in design_source
    assert "service_alignment_stage_messages.py" in design_source
    assert "alignment_readiness_governance.py" in design_source


def test_alignment_agreement_block_has_dedicated_plan_message_and_missing_item_boundaries() -> None:
    design_source = design_boundary_source()

    assert AlignmentAgreementBlockCandidate.__module__ == "loopora.service_alignment_agreement_block_plan"
    assert alignment_agreement_block_plan.__module__ == "loopora.service_alignment_agreement_block_plan"
    assert alignment_block_message.__module__ == "loopora.service_alignment_agreement_block_messages"
    assert alignment_missing_item_label.__module__ == "loopora.service_alignment_agreement_missing_items"
    for filename in (
        "service_alignment_agreement_block_plan.py",
        "service_alignment_agreement_block_messages.py",
        "service_alignment_agreement_missing_items.py",
        "service_alignment_stage_agreement_messages.py",
    ):
        assert filename in design_source


def test_alignment_agreement_stage_has_dedicated_projection_decision_and_message_boundaries() -> None:
    design_source = design_boundary_source()

    assert alignment_visible_agreement_message.__module__ == "loopora.service_alignment_agreement_projection"
    assert alignment_message_confirms_agreement.__module__ == "loopora.service_alignment_agreement_decisions"
    assert alignment_agreement_readiness_checklist_issues.__module__ == "loopora.service_alignment_agreement_decisions"
    assert alignment_user_message_stage_plan.__module__ == "loopora.service_alignment_user_message_stage"
    for filename in (
        "service_alignment_agreement_projection.py",
        "service_alignment_agreement_decisions.py",
        "service_alignment_user_message_stage.py",
    ):
        assert filename in design_source


def test_alignment_decision_options_have_dedicated_catalog_normalization_and_selection_boundaries() -> None:
    design_source = design_boundary_source()

    assert default_alignment_decision_options.__module__ == "loopora.service_alignment_decision_option_catalog"
    assert normalize_alignment_decision_options.__module__ == "loopora.service_alignment_decision_option_normalization"
    assert visible_alignment_decision_options.__module__ == "loopora.service_alignment_decision_option_selection"
    for filename in (
        "service_alignment_decision_option_catalog.py",
        "service_alignment_decision_option_normalization.py",
        "service_alignment_decision_option_selection.py",
        "service_alignment_decision_options.py",
    ):
        assert filename in design_source
