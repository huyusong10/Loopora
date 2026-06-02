from __future__ import annotations

from pathlib import Path

from executor_architecture_test_support import design_contracts_source, loopora_source
from loopora.executor_fake_payloads import alignment_bundle_yaml


def test_fake_alignment_fixtures_keep_payload_data_and_bundle_base_dedicated() -> None:
    payloads_source = loopora_source("executor_alignment_payloads.py")
    preconfirmation_source = loopora_source("executor_alignment_preconfirmation_payloads.py")
    responses_source = loopora_source("executor_alignment_responses.py")
    agreement_responses_source = loopora_source("executor_alignment_agreement_responses.py")
    readiness_responses_source = loopora_source("executor_alignment_readiness_responses.py")
    base_bundle_source = loopora_source("executor_alignment_bundle_base_fixture.py")
    governance_bundle_source = loopora_source("executor_alignment_bundle_governance_fixture.py")
    bundle_variants_source = loopora_source("executor_alignment_bundle_fixtures.py")
    readiness_source = loopora_source("executor_alignment_readiness_payloads.py")
    contracts_source = design_contracts_source()

    assert "from loopora.executor_alignment_readiness_payloads import" in payloads_source
    assert "def alignment_readiness_issue_for_scenario" in readiness_source
    assert "alignment_vague_loop_fit_readiness_evidence" in readiness_source
    assert "alignment_vague_loop_fit_readiness_evidence" not in payloads_source
    assert "from loopora.executor_alignment_preconfirmation_payloads import" in payloads_source
    assert "def alignment_preconfirmation_payload_for_scenario" in preconfirmation_source
    assert "def _alignment_preconfirmation_scenario_payload" in preconfirmation_source
    assert "def _alignment_preconfirmation_scenario_payload" not in payloads_source
    assert "from loopora.executor_alignment_readiness_responses import" in responses_source
    assert "def alignment_readiness_evidence" in readiness_responses_source
    assert "def alignment_improvement_readiness_evidence" in readiness_responses_source
    assert "def alignment_readiness_evidence" not in responses_source
    assert "from loopora.executor_alignment_agreement_responses import" in responses_source
    assert "from loopora.executor_alignment_agreement_responses import" in preconfirmation_source
    for marker in (
        "def alignment_agreement_response",
        "def alignment_improvement_agreement_response",
        "def alignment_refund_agreement_response",
    ):
        assert marker in agreement_responses_source
        assert marker not in responses_source
    assert "from loopora.executor_alignment_bundle_base_fixture import" in bundle_variants_source
    assert "from loopora.executor_alignment_bundle_governance_fixture import" in base_bundle_source
    assert "from loopora.executor_alignment_bundle_governance_fixture import" in bundle_variants_source
    assert "def alignment_bundle_yaml" in base_bundle_source
    assert "def alignment_bundle_governance_sentence" in governance_bundle_source
    assert "def alignment_bundle_governance_role_snippet" in governance_bundle_source
    assert "def _governance_markers_for_workdir" in governance_bundle_source
    assert "def alignment_bundle_governance_sentence" not in base_bundle_source
    assert "def alignment_bundle_governance_role_snippet" not in base_bundle_source
    assert "def alignment_chinese_bundle_yaml" not in base_bundle_source
    assert "def alignment_chinese_bundle_yaml" in bundle_variants_source
    assert "executor_alignment_agreement_responses.py" in contracts_source
    assert "executor_alignment_preconfirmation_payloads.py" in contracts_source
    assert "executor_alignment_bundle_governance_fixture.py" in contracts_source


def test_alignment_fake_bundle_keeps_runtime_judgment_surfaces_visible(sample_workdir: Path) -> None:
    bundle_text = alignment_bundle_yaml(str(sample_workdir.resolve()))

    assert "Execution Strategy, Judgment Tradeoffs, Local Governance, and Residual Risk" in bundle_text
    assert "sequencing drift, lowered tradeoffs, local-governance gaps" in bundle_text
    assert "prove the task contract, execution strategy, judgment tradeoffs, local governance when present" in bundle_text
    assert "Intermediate control points measure weak evidence and fake-done drift" in bundle_text
    assert "trigger a continue / correct / halt decision" in bundle_text
    assert "keep the required evidence target explicit" in bundle_text
    assert "Treat status-only checkpoints as insufficient" in bundle_text
