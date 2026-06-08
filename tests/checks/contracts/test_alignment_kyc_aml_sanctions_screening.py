from __future__ import annotations

from pathlib import Path

from loopora.alignment_traceability_categories import agent_candidate_success_surface_categories
from loopora.alignment_traceability_risk_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories,
)
from loopora.alignment_traceability_rules import (
    alignment_agent_candidate_traceability_issues,
    alignment_bundle_agreement_traceability_issues,
)
from loopora.bundles import load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


KYC_AML_TASK_TEXT = (
    "我要做 marketplace seller onboarding 的 KYC/KYB and AML sanctions screening。成功必须证明 "
    "identity verification、business registry、beneficial owner、document OCR/liveness、address verification、"
    "sanctions/PEP/adverse media/watchlist screening、risk score、manual review queue、appeal/resubmission、"
    "periodic rescreening、provider webhook replay/out-of-order/idempotency、region retention、audit reason codes "
    "和 payout hold/release 都一致。假完成是只让一个 provider sandbox 返回 approved、UI 显示 verified、"
    "只存 provider status、或只跑 happy-path webhook。证据要包含 provider contract fixtures、golden "
    "approved/rejected/manual-review cases、false positive/false negative sanctions samples、expired/fraudulent "
    "document negatives、manual review rubric、decision reason audit trail、webhook signature/replay/order proof、"
    "rescreening job proof、payout hold ledger reconciliation、privacy redaction 和 monitoring alerts。"
)


def test_success_categories_detect_kyc_aml_screening_without_payout_hold_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(KYC_AML_TASK_TEXT)]
    payout_hold_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means payout settlement handles KYC hold, failed payout retry, and provider transfer id."
        )
    ]

    assert "compliance/kyc-aml-sanctions-screening" in labels
    assert "external/provider-contract" in labels
    assert "webhook/signature-replay-ordering" in labels
    assert "payout/settlement-reconciliation" in labels
    assert "billing/ledger-reconciliation" in labels
    assert "quality/human-review" in labels
    assert "privacy/secrets-redaction" in labels
    assert "regression/monitoring-guard" in labels
    assert "payout/settlement-reconciliation" in payout_hold_labels
    assert "compliance/kyc-aml-sanctions-screening" not in payout_hold_labels


def test_fake_done_and_evidence_categories_detect_kyc_aml_screening_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(KYC_AML_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(KYC_AML_TASK_TEXT)
    ]

    assert "compliance/kyc-aml-sanctions-screening" in fake_labels
    assert "compliance/kyc-aml-sanctions-screening" in evidence_labels
    assert "external/provider-contract" in fake_labels
    assert "webhook/signature-replay-ordering" in fake_labels
    assert "quality/human-review" in evidence_labels
    assert "privacy/secrets-redaction" in evidence_labels
    assert "payout/settlement-reconciliation" in evidence_labels


def test_alignment_agreement_requires_kyc_aml_screening_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Show seller onboarding verified after one provider sandbox approved response.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means seller onboarding KYC/KYB and AML sanctions screening proves identity verification, "
                    "business registry, beneficial owners, document OCR and liveness, address verification, sanctions, "
                    "PEP, adverse media, watchlist screening, risk score, manual review queue, appeal/resubmission, "
                    "periodic rescreening, provider webhook replay/out-of-order/idempotency, region retention, audit "
                    "reason codes, and payout hold/release consistency."
                ),
                "fake_done_risks": (
                    "A provider sandbox approved response, UI verified status, stored provider status, or happy-path "
                    "webhook without KYC/KYB, AML sanctions, PEP/adverse media/watchlist, manual review, rescreening, "
                    "reason audit, webhook replay/order, payout hold ledger, privacy, and monitoring proof must block."
                ),
                "evidence_preferences": (
                    "Evidence must include provider contract fixtures, golden approved/rejected/manual-review cases, "
                    "false positive and false negative sanctions samples, expired and fraudulent document negatives, "
                    "manual review rubric, decision reason audit trail, webhook signature/replay/order proof, "
                    "rescreening job proof, payout hold ledger reconciliation, privacy redaction, and monitoring alerts."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "compliance/kyc-aml-sanctions-screening" in issue for issue in issues)
    assert any("fake-done risks" in issue and "compliance/kyc-aml-sanctions-screening" in issue for issue in issues)
    assert any("evidence preferences" in issue and "compliance/kyc-aml-sanctions-screening" in issue for issue in issues)


def test_agent_first_traceability_blocks_provider_sandbox_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Show seller onboarding verified after one provider sandbox approved response.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求 provider sandbox 返回 approved、UI 显示 verified、保存 provider status、happy-path webhook 通过。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: KYC/KYB, AML sanctions, beneficial owners, PEP/adverse media/watchlist, false positives, "
        "fraudulent documents, manual review, rescreening, decision reason audit, webhook replay/order, payout hold ledger, "
        "privacy, and monitoring proof can be handled later.\n"
        "  Owner: compliance platform owner\n"
        "  Follow-up: add KYC/AML screening proof later.\n"
        "  Acceptance path: GateKeeper can pass after sandbox approved and UI verified.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只接 provider sandbox approved、UI verified、provider status 和 happy-path webhook，不处理 "
        "KYC/KYB、AML sanctions、PEP、watchlist、manual review、rescreening、audit reason、payout hold、privacy 或 monitoring proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat sandbox approved, UI verified, stored provider status, and one happy-path webhook as enough for this pass; "
        "KYC/AML screening evidence can be handled later."
    )

    issues = alignment_agent_candidate_traceability_issues(KYC_AML_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "compliance/kyc-aml-sanctions-screening" in issue for issue in issues)
    assert any("fake-done risks" in issue and "compliance/kyc-aml-sanctions-screening" in issue for issue in issues)
    assert any("evidence preferences" in issue and "compliance/kyc-aml-sanctions-screening" in issue for issue in issues)
