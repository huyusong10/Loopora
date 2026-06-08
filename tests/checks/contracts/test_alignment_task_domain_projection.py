from __future__ import annotations

from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, json, yaml
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def test_cli_agent_plan_data_lifecycle_rounds_use_contract_parallel_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-deletion-retention-contract",
    }
    task_message = (
        "Plan a governed Loop for GDPR account deletion and retention. Success must prove account deletion, billing-record "
        "retention exceptions, legal hold, backup expiry handling, search index purge, cache purge, analytics anonymization, "
        "data export suppression, audit trail retention, and tenant isolation. Fake done is a UI delete button, one happy-path "
        "delete API response, a soft-delete flag, or a docs-only retention policy. Evidence should include contract inventory, "
        "negative cases for billing retention exceptions, legal hold, backup expiry, search/cache purge, analytics anonymization, "
        "cross-tenant access, audit log reviewability, and monitoring alerts."
    )

    first_summary = _invoke_data_lifecycle_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_data_lifecycle_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use a data-lifecycle contract-first workflow. Start with Data Lifecycle Contract Inspector freezing "
            "deletion surfaces, retention exceptions, legal hold, backup expiry, search/cache purge, analytics anonymization, export "
            "suppression, audit trail, tenant isolation, and monitoring targets. Deletion Builder may implement only after that handoff. "
            "Then run Privacy Deletion Evidence Inspector and Retention Audit Inspector in parallel: Privacy Deletion verifies account "
            "deletion, tombstones, search/cache purge, analytics anonymization, export suppression, and cross-tenant negatives; Retention "
            "Audit verifies billing retention exceptions, legal hold, backup expiry, audit trail retention, permission, monitoring, and "
            "local governance. GateKeeper must fail closed on UI-delete-only, soft-delete-only, one happy path API response, docs-only "
            "retention policy, missing backup expiry proof, missing retention/legal-hold proof, missing purge/anonymization proof, missing "
            "tenant negatives, or missing audit/monitoring evidence."
        ),
        env=env,
    )
    _assert_data_lifecycle_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_data_lifecycle_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this data lifecycle contract-first parallel evidence direction.",
        env=env,
    )
    _assert_data_lifecycle_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _data_lifecycle_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_data_lifecycle_bundle(bundle_text)


def test_alignment_task_domain_projection_localizes_chinese_visible_focus_without_changing_verify_ids() -> None:
    projection = alignment_task_domain_projection(
        (
            "我要做退款后台修复。成功必须证明普通客服只能看到自己有权限的订单，退款失败会回滚，"
            "audit log 能追踪操作者和原因；我最怕假完成是只跑 happy path 截图。"
        ),
        display_language="zh",
    )

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "payment, refund, proration, invoice, entitlement" not in visible_text
    assert "authorization and negative permission proof" not in visible_text
    assert "支付、退款、按比例调整、发票、权益和余额调整证明" in visible_text
    assert "授权与负向权限证明" in visible_text
    assert "审计日志创建与可审计性" in visible_text
    assert "缺少直接证据时不得通过" in projection.fake_done_focus
    assert "payment-refund-billing" in projection.evidence_verifies
    assert "permission-auth" in projection.evidence_verifies


def test_alignment_task_domain_projection_keeps_english_visible_focus_by_default() -> None:
    projection = alignment_task_domain_projection(
        "Fix refund authorization and prove audit log reviewability.",
    )

    assert "payment, refund, proration, invoice, entitlement" in projection.success_focus
    assert "authorization and negative permission proof" in projection.success_focus


def test_alignment_task_domain_projection_keeps_prompt_asset_ownership_scope_clean() -> None:
    projection = alignment_task_domain_projection(
        (
            "Plan fixed system/developer prompt asset ownership. Success must prove role metadata descriptions, "
            "Agent Native managed entries, runtime prompt prefixes, and alignment compiler prompts load from "
            "system_prompt assets. The system prompt tree must not branch by user language or use .zh/.en refs."
        ),
    )

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "fixed system/developer prompt asset ownership" in visible_text
    assert "authorization and negative permission proof" not in visible_text
    assert "locale formatting, translations" not in visible_text
    assert "prompt-asset-ownership" in projection.evidence_verifies
    assert "permission-auth" not in projection.evidence_verifies
    assert "locale-i18n" not in projection.evidence_verifies


def test_alignment_task_domain_projection_keeps_deletion_retention_scope_clean() -> None:
    projection = alignment_task_domain_projection(
        (
            "Plan a governed data deletion and retention workflow for GDPR erase requests. Success must prove account "
            "deletion, billing-record retention exceptions, anonymized analytics, search-index purge, backup expiry "
            "handling, audit-log retention, and tenant isolation. Fake done is a UI delete button or one happy-path API "
            "response. Inspector must verify negative cases for billing retention exceptions, search purge, analytics "
            "anonymization, backup expiry, and cross-tenant access."
        ),
    )

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "deletion, retention, legal hold, restore, tombstone, search/cache purge, and audit evidence" in visible_text
    assert "tenant isolation and cross-tenant negative cases" in visible_text
    assert "backup integrity, restore drills, RPO/RTO, corruption negatives, and recovery audit proof" in visible_text
    assert "event schema, attribution, dedupe, ordering, privacy, and warehouse reconciliation proof" in visible_text

    assert "tamper-evident audit integrity and retention" not in visible_text
    assert "payment, refund, proration, invoice, entitlement" not in visible_text
    assert "golden eval set, negative examples" not in visible_text
    assert "export/download attempts and report evidence" not in visible_text
    assert "audit-integrity" not in projection.evidence_verifies
    assert "audit-log" in projection.evidence_verifies
    assert "payment-refund-billing" not in projection.evidence_verifies
    assert "eval-set" not in projection.evidence_verifies
    assert "data-export" not in projection.evidence_verifies


def test_alignment_task_domain_projection_keeps_cdc_replication_scope_clean() -> None:
    projection = alignment_task_domain_projection(
        (
            "Plan a governed Loop to add CDC replication from Postgres order tables into a warehouse and "
            "customer-facing read model. Success must prove event ordering, replay idempotency, replication lag bounds, "
            "schema evolution compatibility, initial snapshot plus backfill correctness, delete/tombstone handling, "
            "tenant isolation, and warehouse/read-model reconciliation. Fake done is a green sync job, one row-count "
            "sample, dashboard shows latest, no out-of-order events, no replay duplicate proof, no schema change fixture, "
            "or no lag alert. Required evidence should include out-of-order CDC events, replay from checkpoint, backfill "
            "with concurrent writes, schema-version change, tenant negative cases, lag monitoring, and target "
            "reconciliation queries."
        ),
    )

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "CDC ordering, replay, lag, schema evolution, backfill, and target reconciliation proof" in visible_text
    assert "tenant isolation and cross-tenant negative cases" in visible_text
    assert "monitoring, alerting, and regression guard evidence" in visible_text
    assert "message delivery, recipient targeting, retry, unsubscribe, and audit evidence" not in visible_text
    assert "export/download attempts and report evidence" not in visible_text
    assert "cdc-replication" in projection.evidence_verifies
    assert "tenant-isolation" in projection.evidence_verifies
    assert "monitoring" in projection.evidence_verifies
    assert "message-delivery" not in projection.evidence_verifies
    assert "data-export" not in projection.evidence_verifies


def test_alignment_task_domain_projection_keeps_metric_revenue_retention_from_data_lifecycle() -> None:
    projection = alignment_task_domain_projection(
        (
            "Plan a governed SaaS revenue reporting dashboard for MRR, ARR, churn, expansion, contraction, "
            "and net revenue retention. Success must prove metric definition version, trial/coupon/discount/"
            "refund/proration/downgrade/upgrade/paused-subscription edge cases, FX-date handling, month cutoff "
            "timezone, billing ledger/invoice/provider reconciliation, locked-month backfill, segment permissions, "
            "export consistency, and audit records. Fake done is charts only or CSV only."
        ),
    )

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "metric definition version, edge-case aggregation, FX/cutoff/timezone" in visible_text
    assert "ledger reconciliation and accounting consistency" in visible_text
    assert "authorization and negative permission proof" in visible_text
    assert "deletion, retention, legal hold, restore, tombstone" not in visible_text
    assert "metric-reconciliation" in projection.evidence_verifies
    assert "ledger-reconciliation" in projection.evidence_verifies
    assert "permission-auth" in projection.evidence_verifies
    assert "deletion-retention" not in projection.evidence_verifies


def test_alignment_task_domain_projection_keeps_notification_subscription_scope_clean() -> None:
    projection = alignment_task_domain_projection(
        (
            "我要做 lifecycle campaign email / notification subscription deliverability。成功必须证明只有 "
            "subscribed eligible users 收到 campaign；unsubscribe、preference center、global suppression list 生效；"
            "bounce/complaint/drop provider events、disabled user、tenant filter、locale filter 都正确；"
            "retry/provider replay 不重复发送；provider accepted/delivered/bounced/complained/dropped events 与本地 "
            "delivery audit 能对账；English/Chinese template variables 安全渲染，PII/tokens 不泄露；rate limit、"
            "retry/backoff、DLQ/manual replay、monitoring、audit reason codes、migration/backward compatibility 和 "
            "local governance 都可审计。"
        ),
        display_language="zh",
    )

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "subscription filtering, deliverability" in visible_text
    assert "message delivery, recipient targeting" in visible_text
    assert "PII、secret 和敏感字段遮蔽" in visible_text
    assert "usage metering, quota limits" not in visible_text
    assert "删除、保留、legal hold" not in visible_text
    assert "带审计性的权限证明" not in visible_text
    assert "subscription-deliverability" in projection.evidence_verifies
    assert "message-delivery" in projection.evidence_verifies
    assert "privacy-redaction" in projection.evidence_verifies
    assert "quota-metering" not in projection.evidence_verifies
    assert "deletion-retention" not in projection.evidence_verifies
    assert "permission-audit" not in projection.evidence_verifies


def test_alignment_task_domain_projection_keeps_subscription_entitlement_scope_clean() -> None:
    projection = alignment_task_domain_projection(
        (
            "我要做 B2B SaaS 的订阅套餐升级/降级和权益生效。成功必须证明 Basic 升级到 Pro 立即生效，"
            "降级下个计费周期生效，proration、credit memo、invoice totals、ledger/provider 对账正确，"
            "trial、grace period、billing period boundary、provider webhook 延迟/重复/乱序、重复点击幂等、"
            "团队成员权益传播、历史用量和 quota、权限/tenant 负向、audit、rollback、monitoring 都可验证。"
            "假完成是按钮能点、checkout success only、provider total only 或 happy-path plan change。"
        ),
        display_language="zh",
    )

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "订阅升级/降级生命周期、权益传播" in visible_text
    assert "subscription filtering, deliverability" not in visible_text
    assert "message delivery, recipient targeting" not in visible_text
    assert "usage metering, quota limits" not in visible_text
    assert "tax jurisdiction matrix" not in visible_text
    assert "webhook signature, replay" not in visible_text
    assert "subscription-entitlement" in projection.evidence_verifies
    assert "subscription-deliverability" not in projection.evidence_verifies
    assert "message-delivery" not in projection.evidence_verifies
    assert "tax-compliance" not in projection.evidence_verifies
    assert "webhook-ordering" not in projection.evidence_verifies


def test_alignment_task_domain_projection_keeps_audit_integrity_when_strongly_anchored() -> None:
    projection = alignment_task_domain_projection(
        (
            "Build a compliance audit trail. Success must prove append-only audit log entries with a tamper-evident "
            "hash chain, WORM storage, retention policy, legal hold, SIEM export reconciliation, monotonic timestamp, "
            "clock skew handling, and sequence gap alerts."
        ),
    )

    visible_text = " ".join([projection.success_focus, projection.fake_done_focus, projection.evidence_focus])
    assert "tamper-evident audit integrity and retention" in visible_text
    assert "audit-integrity" in projection.evidence_verifies


def _invoke_data_lifecycle_plan_round(
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


def _assert_data_lifecycle_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Data Lifecycle Contract Inspector" in agreement_text
    assert "Privacy Deletion Evidence Inspector" in agreement_text
    assert "Retention Audit Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task anchor through an evidence-first repair Loop" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_data_lifecycle_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("backup expiry", "legal hold", "analytics anonymization", "tenant isolation"):
        assert term in ready_projection_text
    assert "Confirm; use this data lifecycle" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _data_lifecycle_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_data_lifecycle_bundle(bundle_text: str) -> None:
    workflow = yaml.safe_load(bundle_text)["workflow"]
    assert workflow["preset"] == "data-lifecycle-contract-parallel-deletion-retention"
    assert [step["id"] for step in workflow["steps"]] == [
        "data_lifecycle_contract_inspection_step",
        "deletion_builder_step",
        "privacy_deletion_evidence_inspection_step",
        "retention_audit_inspection_step",
        "data_lifecycle_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["data_lifecycle_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "data_lifecycle_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "data_lifecycle_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "data_lifecycle_contract_inspection_step",
        "deletion_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "data_lifecycle_contract_inspection_step",
        "deletion_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "data_lifecycle_contract_inspection_step",
        "deletion_builder_step",
        "privacy_deletion_evidence_inspection_step",
        "retention_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "deletion-retention",
        "tenant-isolation",
        "privacy-redaction",
        "audit-log",
        "permission-auth",
        "monitoring",
        "backup-restore",
        "cache-invalidation",
        "data-export",
        "event-integrity",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Data Lifecycle Deletion Retention Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this data lifecycle" not in bundle_text
