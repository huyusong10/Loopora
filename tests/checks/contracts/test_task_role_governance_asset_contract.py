from __future__ import annotations

import json
from pathlib import Path

from compacted_contract_support import assert_contains_all
from loopora.alignment_guidance import load_alignment_guidance_assets


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_task_role_governance_prompt_fragments_live_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    asset_text = "\n".join(assets.task_role_governance.values())
    assert_contains_all(
        asset_text,
        (
            "Builder reads AGENTS.md, design/README.md, design/, and tests/",
            "Inspector must verify AGENTS.md, design/README.md, design/, and tests/",
            "GateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/",
            "Respect project-local governance when AGENTS.md, design/README.md, design/, or tests/ apply.",
        ),
    )

    bundle_fixture_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_fixtures.py").read_text(encoding="utf-8")
    for snippet in (
        "Builder reads AGENTS.md, design/README.md, design/, and tests/ before changing code",
        "Inspector must verify AGENTS.md, design/README.md, design/, and tests/ obligations against the result",
        "GateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ responsibilities",
        "Respect project-local governance when AGENTS.md, design/README.md, design/, or tests/ apply.",
    ):
        assert snippet not in bundle_fixture_source


def test_task_domain_projection_prompt_fragments_live_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    asset_text = json.dumps(assets.task_domain_projection, ensure_ascii=False)
    assert_contains_all(
        asset_text,
        (
            "payment, refund, proration, invoice, entitlement",
            "authorization and negative permission proof",
            "backup integrity, restore drills, RPO/RTO",
            "支付、退款、按比例调整、发票、权益和余额调整证明",
            "task_anchor",
            "payment-refund-billing",
            "backup-restore",
        ),
    )

    projection_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_task_projection.py").read_text(encoding="utf-8")
    for snippet in (
        "payment, refund, proration, invoice, entitlement",
        "authorization and negative permission proof",
        "backup integrity, restore drills, RPO/RTO",
        "支付、退款、按比例调整、发票、权益和余额调整证明",
        'DEFAULT_EVIDENCE_VERIFIES = ["task_anchor"',
        '"payment/refund/billing": "payment-refund-billing"',
        '"backup/restore-recovery": "backup-restore"',
    ):
        assert snippet not in projection_source


def test_task_specific_role_fixture_prompt_fragments_live_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    asset_text = json.dumps(assets.task_role_fixtures, ensure_ascii=False)
    task_fixtures = assets.task_role_fixtures["tasks"]
    assert set(task_fixtures) >= {
        "generic_task_anchor",
        "refund_repair",
        "search_refactor_improvement",
        "data_residency",
        "support_impersonation",
        "kyc_aml_screening",
        "payment_webhook_ledger",
        "identity_sso",
        "key_rotation",
        "prompt_asset_ownership",
        "backup_restore_recovery",
        "audit_log_integrity_retention",
        "database_schema_migration",
        "cdc_replication_consistency",
        "metric_reporting_reconciliation",
        "dispute_chargeback_lifecycle",
        "payout_settlement_reconciliation",
        "analytics_experiment_instrumentation",
        "notification_subscription_deliverability",
        "data_lifecycle_deletion_retention",
        "feature_flag_rollout",
        "cache_invalidation_consistency",
        "data_import_validation",
        "usage_quota_metering",
        "tax_calculation_compliance",
        "inventory_reservation_consistency",
        "file_upload_storage_safety",
        "auth_session_token_lifecycle",
        "authorization_policy",
        "incident_root_cause",
        "rag_long_chain",
        "search_quality",
        "schedule_phase",
    }
    for task_fixture in task_fixtures.values():
        for role in task_fixture["roles"]:
            assert isinstance(role["prompt_body"], str)
            assert isinstance(role["name"], dict)
            assert isinstance(role["description"], dict)
            assert isinstance(role["posture"], dict)
    assert_contains_all(
        asset_text,
        (
            "generic_task_anchor",
            "Build the smallest real loop for the task anchor.",
            "Build the narrow refund self-service path carefully.",
            "Inspect the Builder handoff against refund authorization",
            "Read the Refund Repair Guide handoff before editing.",
            "Freeze the source Search Loop baseline",
            "Disprove complexity only moved elsewhere",
            "Read-only freeze the EU/US data-plane inventory",
            "Read-only freeze provider event schemas",
            "Read-only freeze fixed system/developer prompt surfaces",
            "Freeze document-version, source-span, retrieval ACL",
            "feature_flag_rollout",
            "cache_invalidation_consistency",
            "Read-only freeze default-off behavior, cohort targeting",
            "Build feature flag, cohort targeting, percentage rollout",
            "Read-only freeze price surfaces, cache-key inventory",
            "Build price-update invalidation across PDP/cart/checkout/API/CDN/Redis/read-model",
            "Read-only freeze CSV field mapping",
            "Build the import pipeline from the contract handoff",
            "Verify PII redaction in logs and row errors",
            "Read-only freeze usage event schema",
            "Build usage metering, quota enforcement",
            "Read-only freeze taxable nexus",
            "Build tax calculation compliance",
            "Read-only freeze audit event matrix",
            "Build audit trail integrity and retention",
            "Read-only freeze database schema migration and backfill contract",
            "Build the database schema migration slice from the contract handoff",
            "Read-only freeze CDC replication consistency contract",
            "Build the CDC replication pipeline from the contract handoff",
            "Read-only freeze revenue metric reporting contract",
            "Build the revenue reporting dashboard from the contract handoff",
            "Read-only freeze the dispute and chargeback lifecycle contract",
            "Build the dispute and chargeback lifecycle slice from the dispute contract handoff",
            "Read-only freeze marketplace payout settlement contract",
            "Build the marketplace seller payout settlement slice from the payout contract handoff",
            "Read-only freeze analytics instrumentation and experiment exposure contract",
            "Build onboarding analytics instrumentation and experiment exposure",
            "Read-only freeze notification subscription-deliverability contract",
            "Build campaign email deliverability and subscription preference enforcement",
            "Read-only freeze SKU stock invariants",
            "Build checkout reservation, hold TTL/expiry release",
            "Read-only freeze MIME/content sniffing",
            "Build upload validation, malware scanning",
            "Read-only freeze access token expiry",
            "Build token expiry, refresh rotation and reuse detection",
            "实现前只读固定 default-off",
            "实现前只读固定 price surfaces",
        ),
    )

    bundle_fixture_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_fixtures.py").read_text(encoding="utf-8")
    for snippet in (
        "Build the smallest real loop for the task anchor.",
        "Build the narrow refund self-service path carefully.",
        "Inspect the Builder handoff against refund authorization",
        "Read the Refund Repair Guide handoff before editing.",
        "Freeze the source Search Loop baseline",
        "Disprove complexity only moved elsewhere",
        "Read-only freeze the EU/US data-plane inventory",
        "Read-only freeze provider event schemas",
        "Read-only freeze fixed system/developer prompt surfaces",
        "Freeze document-version, source-span, retrieval ACL",
        "Read-only freeze default-off behavior, cohort targeting",
        "Build feature flag, cohort targeting, percentage rollout",
        "Read-only freeze price surfaces, cache-key inventory",
        "Build price-update invalidation across PDP/cart/checkout/API/CDN/Redis/read-model",
        "Read-only freeze CSV field mapping",
        "Build the import pipeline from the contract handoff",
        "Verify PII redaction in logs and row errors",
        "Read-only freeze usage event schema",
        "Build usage metering, quota enforcement",
        "Read-only freeze taxable nexus",
        "Build tax calculation compliance",
        "Read-only freeze audit event matrix",
        "Build audit trail integrity and retention",
        "Read-only freeze database schema migration and backfill contract",
        "Build the database schema migration slice from the contract handoff",
        "Read-only freeze CDC replication consistency contract",
        "Build the CDC replication pipeline from the contract handoff",
        "Read-only freeze revenue metric reporting contract",
        "Build the revenue reporting dashboard from the contract handoff",
        "Read-only freeze the dispute and chargeback lifecycle contract",
        "Build the dispute and chargeback lifecycle slice from the dispute contract handoff",
        "Read-only freeze marketplace payout settlement contract",
        "Build the marketplace seller payout settlement slice from the payout contract handoff",
        "Read-only freeze analytics instrumentation and experiment exposure contract",
        "Build onboarding analytics instrumentation and experiment exposure",
        "Read-only freeze notification subscription-deliverability contract",
        "Build campaign email deliverability and subscription preference enforcement",
        "Read-only freeze SKU stock invariants",
        "Build checkout reservation, hold TTL/expiry release",
        "Read-only freeze MIME/content sniffing",
        "Build upload validation, malware scanning",
        "Read-only freeze access token expiry",
        "Build token expiry, refresh rotation and reuse detection",
        "实现前只读固定 default-off",
        "实现前只读固定 price surfaces",
    ):
        assert snippet not in bundle_fixture_source
