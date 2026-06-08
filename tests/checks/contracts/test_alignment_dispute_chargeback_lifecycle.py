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


DISPUTE_CHARGEBACK_TASK_TEXT = (
    "我要做支付争议和 chargeback lifecycle。成功必须证明 provider dispute.created/updated/closed webhook、"
    "retrieval request、representment evidence submission deadline、issuer/acquirer reason code、provisional "
    "credit/debit、fee、win/loss、partial dispute、duplicate dispute、refund overlap、order fulfillment evidence、"
    "customer notification、merchant response SLA、ledger entries、invoice/balance adjustment、payout hold/release、"
    "audit trail 和 monitoring 都一致。假完成是只让一个 dispute webhook 改 UI 状态、只在 Stripe dashboard "
    "看 won/lost、只保存 provider dispute id、或 happy-path close。证据要包含 provider fixture contract、"
    "signature/replay/out-of-order webhook cases、deadline scheduler proof、evidence package artifact、ledger "
    "reconciliation、refund/chargeback overlap negatives、notification delivery proof、merchant SLA cases、"
    "audit reason refs 和 failed/stale dispute alerts。"
)


def test_cli_agent_plan_dispute_chargeback_rounds_use_contract_parallel_lifecycle_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-dispute-chargeback-contract",
    }

    first_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=DISPUTE_CHARGEBACK_TASK_TEXT,
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    first_summary = json.loads(first_result.stdout)["summary"]

    assert first_result.exit_code == 0, first_result.stdout
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=(
            "补充判断：采用 dispute lifecycle contract-first workflow。先由只读 Dispute Contract Inspector 固定 "
            "provider dispute.created/updated/closed fixtures、signature/replay/out-of-order webhook contract、retrieval "
            "request、representment evidence package deadline、issuer/acquirer reason code、provisional credit/debit、"
            "fee、win/loss、partial dispute、duplicate dispute、refund overlap、order fulfillment evidence、customer "
            "notification、merchant response SLA、ledger entry、invoice/balance adjustment、payout hold/release、audit "
            "reason refs、failed/stale dispute monitoring 和本地治理证据目标。Chargeback Lifecycle Builder 只能读取该 "
            "handoff 后实现。然后 Dispute Evidence Inspector 与 Ledger Notification Inspector 并行检查同一个产物。"
            "GateKeeper 必须在 UI-status-only、Stripe dashboard won/lost-only、provider dispute id-only、happy-path close、"
            "无 evidence package、无 deadline proof、无 refund overlap negative、无 ledger/payout reconciliation、"
            "无 notification/SLA、无 audit 或无 monitoring 时 fail closed。"
        ),
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    second_summary = json.loads(second_result.stdout)["summary"]

    assert second_result.exit_code == 0, second_result.stdout
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Dispute Contract Inspector" in agreement_text
    assert "Chargeback Lifecycle Builder" in agreement_text
    assert "Dispute Evidence Inspector" in agreement_text
    assert "Ledger Notification Inspector" in agreement_text
    assert "Notification Contract Inspector" not in agreement_text
    assert "Campaign Email Builder" not in agreement_text

    third_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="确认，采用这个 dispute/chargeback lifecycle 方向。",
        entry_source="codex_project_skill",
        json_output=True,
        compact_json_output=True,
        env=env,
    )
    third_summary = json.loads(third_result.stdout)["summary"]

    assert third_result.exit_code == 0, third_result.stdout
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == first_summary["alignment_session_id"]
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    assert "dispute lifecycle" in ready_projection_text
    assert "notification subscription-deliverability" not in ready_projection_text
    assert "Campaign Email" not in ready_projection_text

    bundle_text = (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / third_summary["alignment_session_id"]
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")
    bundle = yaml.safe_load(bundle_text)
    assert bundle["metadata"]["name"] == "争议 Chargeback 生命周期 Loop"
    role_keys = {role["key"] for role in bundle["role_definitions"]}
    assert {
        "dispute-contract-inspector",
        "chargeback-lifecycle-builder",
        "dispute-evidence-inspector",
        "ledger-notification-inspector",
        "dispute-chargeback-gatekeeper",
    } <= role_keys
    workflow = bundle["workflow"]
    assert workflow["preset"] == "dispute-chargeback-contract-parallel-lifecycle"
    assert [step["id"] for step in workflow["steps"]] == [
        "dispute_contract_inspection_step",
        "chargeback_lifecycle_builder_step",
        "dispute_evidence_inspection_step",
        "ledger_notification_inspection_step",
        "dispute_chargeback_gatekeeper_step",
    ]
    assert workflow["steps"][2]["parallel_group"] == "dispute_chargeback_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "dispute_chargeback_review_pack"
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "dispute-chargeback",
        "webhook-ordering",
        "evidence-deadline",
        "ledger-reconciliation",
        "payout-settlement",
        "message-delivery",
        "audit-log",
        "monitoring",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "notification-subscription-deliverability" not in gatekeeper_verifies
    assert "Notification Contract Inspector" not in bundle_text
    assert "Campaign Email Builder" not in bundle_text


def test_success_categories_detect_dispute_lifecycle_without_payout_chargeback_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(DISPUTE_CHARGEBACK_TASK_TEXT)]
    payout_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means seller balance ledger accounts for captured, refunded, and chargeback orders."
        )
    ]

    assert "payment/dispute-chargeback-lifecycle" in labels
    assert "webhook/signature-replay-ordering" in labels
    assert "billing/ledger-reconciliation" in labels
    assert "payout/settlement-reconciliation" in labels
    assert "notification/message" in labels
    assert "audit/log" in labels
    assert "regression/monitoring-guard" in labels
    assert "payout/settlement-reconciliation" in payout_labels
    assert "payment/dispute-chargeback-lifecycle" not in payout_labels


def test_alignment_task_domain_projection_keeps_dispute_from_subscription_scope() -> None:
    projection = alignment_task_domain_projection(DISPUTE_CHARGEBACK_TASK_TEXT, display_language="zh")
    visible_text = "\n".join(
        [projection.success_focus, projection.fake_done_focus, projection.evidence_focus, "\n".join(projection.evidence_verifies)]
    )

    assert "dispute lifecycle" in visible_text
    assert "subscription-deliverability" not in visible_text


def test_fake_done_and_evidence_categories_detect_dispute_lifecycle_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(DISPUTE_CHARGEBACK_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(DISPUTE_CHARGEBACK_TASK_TEXT)
    ]

    assert "payment/dispute-chargeback-lifecycle" in fake_labels
    assert "payment/dispute-chargeback-lifecycle" in evidence_labels
    assert "webhook/signature-replay-ordering" in fake_labels
    assert "billing/ledger-reconciliation" in evidence_labels
    assert "payout/settlement-reconciliation" in evidence_labels
    assert "regression/monitoring-guard" in evidence_labels


def test_alignment_agreement_requires_dispute_lifecycle_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Update dispute UI status after one provider webhook and store provider dispute id.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means chargeback lifecycle proves dispute.created/updated/closed webhooks, retrieval "
                    "request, representment evidence submission deadline, issuer/acquirer reason code, provisional "
                    "credit/debit, fees, win/loss, partial dispute, duplicate dispute, refund overlap, order fulfillment "
                    "evidence, customer notification, merchant response SLA, ledger entries, invoice/balance adjustment, "
                    "payout hold/release, audit trail, and monitoring."
                ),
                "fake_done_risks": (
                    "A dispute webhook changing UI status, Stripe dashboard won/lost, stored provider dispute id, or "
                    "happy-path close without deadline, evidence package, webhook replay/order, ledger, refund overlap, "
                    "notification, merchant SLA, payout hold, audit, and monitoring proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include provider fixture contract, signature/replay/out-of-order webhook cases, "
                    "deadline scheduler proof, evidence package artifact, ledger reconciliation, refund/chargeback "
                    "overlap negatives, notification delivery proof, merchant SLA cases, audit reason refs, and "
                    "failed/stale dispute alerts."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "payment/dispute-chargeback-lifecycle" in issue for issue in issues)
    assert any("fake-done risks" in issue and "payment/dispute-chargeback-lifecycle" in issue for issue in issues)
    assert any("evidence preferences" in issue and "payment/dispute-chargeback-lifecycle" in issue for issue in issues)


def test_agent_first_traceability_blocks_dashboard_status_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Update payment case UI status after one provider event and store provider case id.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求 provider event 改 UI 状态、dashboard 看 outcome、保存 provider case id、happy-path close。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: deadlines, package artifacts, event replay/order, ledger reconciliation, overlap "
        "negatives, notification delivery, merchant response timing, payout holds, audit refs, and stuck case alerts "
        "can be handled later.\n"
        "  Owner: payments platform owner\n"
        "  Follow-up: add full payment case proof later.\n"
        "  Acceptance path: GateKeeper can pass after UI status and provider case id work.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 provider event 改 UI 状态、保存 provider case id 和 happy-path close，不处理 deadlines、package artifacts、"
        "event replay/order、ledger、overlap negatives、notification、merchant response timing、payout holds、audit 或 monitoring proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat UI status, provider case id, and happy-path close as enough for this pass; full payment case proof can "
        "be handled later."
    )

    issues = alignment_agent_candidate_traceability_issues(DISPUTE_CHARGEBACK_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "payment/dispute-chargeback-lifecycle" in issue for issue in issues)
    assert any("fake-done risks" in issue and "payment/dispute-chargeback-lifecycle" in issue for issue in issues)
    assert any("evidence preferences" in issue and "payment/dispute-chargeback-lifecycle" in issue for issue in issues)
