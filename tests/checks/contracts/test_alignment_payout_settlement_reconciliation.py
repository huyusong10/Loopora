from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
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
from loopora.executor_alignment_task_projection import alignment_task_domain_projection
from loopora.executor_fake_payloads import alignment_bundle_yaml


PAYOUT_SETTLEMENT_TASK_TEXT = (
    "我要做 marketplace seller payout。成功必须证明 order captured/refunded/chargeback 都进入 seller balance ledger，"
    "platform fee、tax、adjustment、hold/reserve 和 negative balance 正确计算，payout batch cutoff / timezone / "
    "currency / FX rounding 正确，provider transfer id、bank account、KYC hold、failed payout、retry 和 reversal 幂等，"
    "不会 double payout，Stripe/Adyen payout report、本地 ledger、invoice 和 bank statement 能对账，"
    "seller/tenant 访问不能串数据，audit log 记录 payout batch id、ledger entry id、provider transfer id、actor、"
    "failure reason，监控要发现 stuck payout、failed transfer 和 reconciliation mismatch；只有 Stripe dashboard "
    "显示 paid、一笔 test payout 成功或 UI 显示余额减少必须阻断。"
)


def test_cli_agent_plan_payout_settlement_rounds_use_parallel_reconciliation_workflow(
    sample_workdir: Path,
) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-payout-settlement-reconciliation",
    }
    task_message = (
        "Plan a governed Loop for marketplace seller payout settlement. Success must prove captured, refunded, "
        "and chargeback orders enter seller balance ledger; platform fee, tax, adjustments, holds/reserves, and "
        "negative balances calculate correctly; payout batch cutoff, timezone, currency, and FX rounding are correct; "
        "provider transfer id, bank account, KYC hold, failed payout, retry, reversal, and double-payout prevention "
        "are idempotent; Stripe/Adyen payout report, local ledger, invoice, and bank statement reconcile; seller and "
        "tenant access cannot cross data; audit logs record payout batch id, ledger entry id, provider transfer id, "
        "actor, and failure reason; monitoring catches stuck payout, failed transfer, and reconciliation mismatch. "
        "Fake done is Stripe dashboard paid, one test payout succeeds, UI balance decreases, no seller ledger proof, "
        "no failed/reversal negative, no provider-bank reconciliation, no tenant negative, no audit trail, or no monitoring."
    )

    first_summary = _invoke_payout_settlement_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_payout_settlement_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a payout settlement contract-first workflow. Start with a read-only Payout "
            "Contract Inspector freezing seller balance ledger semantics, captured/refunded/chargeback order samples, "
            "platform fee/tax/adjustment/hold/reserve/negative-balance rules, payout batch cutoff/timezone/currency/FX "
            "rounding policy, provider transfer id and bank account fixtures, KYC hold, failed payout, retry/reversal "
            "idempotency, double-payout prevention, provider payout report/local ledger/invoice/bank statement "
            "reconciliation queries, seller/tenant access boundaries, audit fields, monitoring alerts, and local "
            "governance proof targets. Payout Settlement Builder implements only after that handoff. Then run Settlement "
            "Reconciliation Inspector and Access Idempotency Inspector in parallel: Settlement Reconciliation verifies "
            "seller ledger entries, fee/tax/hold calculations, payout cutoff/FX rounding, provider/local/invoice/bank "
            "reconciliation, stuck payout and mismatch alerts; Access Idempotency verifies tenant access negatives, "
            "failed payout retry, reversal idempotency, double-payout negatives, KYC hold behavior, audit records, and "
            "local governance. GateKeeper must fail closed on dashboard-paid-only, test-payout-only, UI-balance-only, "
            "no seller ledger proof, no failed/reversal negative, no double-payout negative, no provider-bank "
            "reconciliation, no tenant negative, no audit trail, no monitoring, or skipped local governance."
        ),
        env=env,
    )
    _assert_payout_settlement_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_payout_settlement_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this payout settlement direction.",
        env=env,
    )
    _assert_payout_settlement_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _payout_settlement_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_payout_settlement_bundle(bundle_text)


def test_success_categories_detect_payout_settlement_without_inventory_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(PAYOUT_SETTLEMENT_TASK_TEXT)]
    inventory_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means inventory reservation consistency proves SKU checkout cannot oversell and reservation "
            "hold TTL expiry releases stock."
        )
    ]
    weak_test_payout_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "成功必须让一笔 test payout 成功，Stripe dashboard 显示 paid，UI 显示余额减少。"
        )
    ]

    assert "payout/settlement-reconciliation" in labels
    assert "billing/ledger-reconciliation" in labels
    assert "payment/refund/billing" in labels
    assert "idempotency/duplicate-prevention" in labels
    assert "audit/log" in labels
    assert "permission/auth" in labels
    assert "regression/monitoring-guard" in labels
    assert "inventory/reservation-consistency" not in labels
    assert "inventory/reservation-consistency" in inventory_labels
    assert "payout/settlement-reconciliation" not in inventory_labels
    assert "payout/settlement-reconciliation" not in weak_test_payout_labels


def test_alignment_task_domain_projection_keeps_payout_from_kyc_or_dispute_scope() -> None:
    projection = alignment_task_domain_projection(PAYOUT_SETTLEMENT_TASK_TEXT)

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "seller balance ledger, payout batch cutoff" in visible_text
    assert "ledger reconciliation and accounting consistency" in visible_text
    assert "tenant isolation and cross-tenant negative cases" in visible_text
    assert "identity/business verification, sanctions/PEP negatives" not in visible_text
    assert "dispute lifecycle, evidence deadlines" not in visible_text
    assert "payout-settlement" in projection.evidence_verifies
    assert "ledger-reconciliation" in projection.evidence_verifies
    assert "idempotency" in projection.evidence_verifies
    assert "tenant-isolation" in projection.evidence_verifies
    assert "kyc-aml-screening" not in projection.evidence_verifies
    assert "dispute-chargeback" not in projection.evidence_verifies


def test_fake_done_and_evidence_categories_detect_payout_settlement_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(PAYOUT_SETTLEMENT_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(PAYOUT_SETTLEMENT_TASK_TEXT)
    ]

    assert "payout/settlement-reconciliation" in fake_labels
    assert "payout/settlement-reconciliation" in evidence_labels
    assert "billing/ledger-reconciliation" in evidence_labels
    assert "idempotency/duplicate-prevention" in evidence_labels
    assert "permission/auth" in evidence_labels
    assert "regression/monitoring-guard" in evidence_labels
    assert "inventory/reservation-consistency" not in fake_labels


def test_alignment_agreement_requires_payout_settlement_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Run one test payout and show the seller balance decreasing.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means marketplace payout settlement proves captured/refunded/chargeback orders enter "
                    "the seller balance ledger, platform fee, tax, adjustment, hold/reserve, negative balance, "
                    "batch cutoff, timezone, currency and FX rounding are correct, provider transfer id, bank account, "
                    "KYC hold, failed payout, retry and reversal are idempotent, double payout is blocked, Stripe/Adyen "
                    "payout report, local ledger, invoice and bank statement reconcile, tenant access is isolated, "
                    "and audit records payout batch id and provider transfer id."
                ),
                "fake_done_risks": (
                    "A Stripe dashboard paid state, one test payout, or UI balance decrease without seller balance "
                    "ledger, batch cutoff, failed payout/reversal, double-payout prevention, provider/bank "
                    "reconciliation, tenant access, monitoring, and audit proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include seller balance ledger entries for captured/refund/chargeback, fee/tax/"
                    "adjustment/hold calculations, batch cutoff/timezone/currency/FX proofs, provider transfer and "
                    "bank account fixtures, KYC hold, failed payout, retry and reversal idempotency, double-payout "
                    "negative checks, payout report/local ledger/invoice/bank-statement reconciliation, tenant "
                    "access samples, monitoring alerts, and audit logs."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "payout/settlement-reconciliation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "payout/settlement-reconciliation" in issue for issue in issues)
    assert any("evidence preferences" in issue and "payout/settlement-reconciliation" in issue for issue in issues)


def _invoke_payout_settlement_plan_round(
    runner: CliRunner,
    sample_workdir: Path,
    *,
    message: str,
    env: dict[str, str],
) -> dict:
    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=message,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    assert result.exit_code == 0, result.stdout
    return json.loads(result.stdout)["summary"]


def _assert_payout_settlement_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Payout Contract Inspector" in agreement_text
    assert "Payout Settlement Builder" in agreement_text
    assert "Settlement Reconciliation Inspector" in agreement_text
    assert "Access Idempotency Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "KYC/AML Builder" not in agreement_text
    assert "Compliance Contract Inspector" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_payout_settlement_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("seller ledger", "provider/bank", "double-payout", "tenant", "audit", "monitoring"):
        assert term in ready_projection_text
    assert "identity/business verification" not in ready_projection_text
    assert "dispute lifecycle" not in ready_projection_text
    assert "Confirm; use this payout settlement direction" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _payout_settlement_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_payout_settlement_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    spec_markdown = bundle["spec"]["markdown"]
    assert bundle["metadata"]["name"] == "Payout Settlement Reconciliation Loop"
    assert bundle["loop"]["name"] == "Payout Settlement Reconciliation Loop"
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "payout-contract-inspector",
        "payout-settlement-builder",
        "settlement-reconciliation-inspector",
        "access-idempotency-inspector",
        "payout-settlement-gatekeeper",
    ]
    assert workflow["preset"] == "payout-settlement-contract-parallel-reconciliation"
    assert [step["id"] for step in workflow["steps"]] == [
        "payout_contract_inspection_step",
        "payout_settlement_builder_step",
        "settlement_reconciliation_inspection_step",
        "access_idempotency_inspection_step",
        "payout_settlement_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["payout_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "payout_settlement_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "payout_settlement_review_pack"
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "payout_contract_inspection_step",
        "payout_settlement_builder_step",
        "settlement_reconciliation_inspection_step",
        "access_idempotency_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "payout-settlement",
        "ledger-reconciliation",
        "provider-contract",
        "provider-bank-reconciliation",
        "idempotency",
        "double-payout",
        "tenant-isolation",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "kyc-aml-screening" not in gatekeeper_verifies
    assert "dispute-chargeback" not in gatekeeper_verifies
    assert "Payout Settlement Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Compliance Contract Inspector" not in bundle_text
    assert "KYC/AML Builder" not in bundle_text
    assert (
        "Payout Contract Inspector -> Payout Settlement Builder -> "
        "[Settlement Reconciliation Inspector + Access Idempotency Inspector] -> Payout Settlement GateKeeper"
    ) in spec_markdown


def test_agent_first_traceability_blocks_test_payout_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Run one test payout, show Stripe dashboard paid, and decrease the seller balance in the UI.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求一笔 test payout 成功、Stripe dashboard 显示 paid、UI 显示余额减少。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: seller balance ledger, payout batch cutoff, failed payout, reversal, double-payout "
        "prevention, provider/bank reconciliation, tenant access, monitoring, and audit proof can be handled later.\n"
        "  Owner: payments owner\n"
        "  Follow-up: add payout settlement hardening later.\n"
        "  Acceptance path: GateKeeper can pass after one test payout succeeds and the UI balance decreases.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现一笔 test payout、Stripe dashboard paid 和 UI 余额减少，不处理 seller balance ledger、"
        "batch cutoff、failed payout、reversal、double-payout prevention、provider/bank reconciliation、"
        "tenant access、monitoring 或 audit proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat seller balance ledger, batch cutoff, failed payout, reversal, double-payout prevention, provider/bank "
        "reconciliation, tenant access, monitoring, and audit proof as later residual risk; only check one test payout, "
        "Stripe dashboard paid, and UI balance decrease."
    )

    issues = alignment_agent_candidate_traceability_issues(PAYOUT_SETTLEMENT_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "payout/settlement-reconciliation" in issue for issue in issues)
    assert any("fake-done risks" in issue and "payout/settlement-reconciliation" in issue for issue in issues)
    assert any("evidence preferences" in issue and "payout/settlement-reconciliation" in issue for issue in issues)
