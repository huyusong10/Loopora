from __future__ import annotations

import json
from pathlib import Path

from alignment_test_support import (
    _agreement_response_boundary_sources,
    _assert_agreement_evidence_design_inventory,
    _assert_agreement_evidence_import_boundary,
    _assert_agreement_readiness_asset_boundary,
    _assert_agreement_task_dispatch_boundary,
    _assert_agreement_task_response_design_inventory,
    _assert_agreement_task_response_domain_boundaries,
)
from executor_architecture_test_support import (
    _assert_bundle_task_routing_appender_boundary,
    _assert_bundle_task_routing_dispatch_boundary,
    _assert_bundle_task_spec_scaffold_domain_boundaries,
    _assert_task_workflow_design_inventory,
    _assert_task_workflow_dispatch_boundary,
    _assert_task_workflow_prose_boundaries,
    _assert_task_workflow_shape_boundaries,
    _bundle_task_routing_boundary_sources,
    _task_workflow_boundary_sources,
    design_contracts_source,
    loopora_source,
)
from executor_bundle_routing_inventory_checks import _assert_bundle_task_routing_design_inventory
from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
from loopora.executor_alignment_agreement_task_dispatch import alignment_task_anchored_agreement_response
from loopora.executor_alignment_bundle_fixtures import alignment_chinese_bundle_yaml, alignment_task_anchored_repair_bundle_yaml
from loopora.executor_alignment_task_projection import alignment_task_domain_projection
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_alignment_traceability_projection import alignment_bundle_visible_text
import yaml


SPECIALIZED_WORKFLOW_TASKS = {
    "kyc_aml": (
        "Plan marketplace seller onboarding KYC/KYB and AML sanctions screening with provider contracts, "
        "sanctions negatives, manual review, webhook replay, payout ledger, privacy, and monitoring."
    ),
    "key_rotation": (
        "Plan customer API key and service account secret rotation with old/new overlap, revoked-key negative calls, "
        "hash/KMS storage, audit, rollback, and monitoring."
    ),
    "payment_webhook": (
        "Plan payment provider webhook ledger handling with signature verification, replay/idempotency, out-of-order "
        "events, DLQ, ledger reconciliation, refunds, disputes, payout updates, audit, and monitoring."
    ),
    "identity_sso": (
        "Plan enterprise SAML/OIDC SSO with SCIM provisioning, tenant binding, forged assertion negatives, deprovisioning, role mapping, audit, and monitoring."
    ),
    "authorization_policy": (
        "Plan authorization policy consistency across UI, API, background jobs, exports, cache, audit log, "
        "role hierarchy, field permissions, temporary access, and tenant boundary."
    ),
    "prompt_asset": (
        "Plan fixed system/developer prompt asset ownership: move hardcoded prompts into assets, keep locale-neutral "
        "system prompt loading, verify runtime rendering, and placeholder safety."
    ),
    "data_residency": (
        "Plan EU/US data residency regional isolation across DB, storage, search, cache, queue, backup, logs, "
        "analytics, processor DPA, key region, failover, migration, export, audit, and egress monitoring."
    ),
    "notification": (
        "Plan lifecycle campaign email deliverability and subscription preferences with unsubscribe, suppression list, "
        "bounce/complaint/drop events, provider webhook replay, duplicate-send negatives, template privacy, audit, and monitoring."
    ),
    "analytics_experiment": (
        "Plan mobile onboarding analytics instrumentation and A/B experiment exposure with event schema, identity merge, "
        "consent negatives, offline replay dedupe, warehouse reconciliation, assignment stability, exposure, and monitoring."
    ),
    "rag_long_chain": (
        "Plan enterprise knowledge-base RAG support chatbot long-chain workflow with document ingestion, retrieval ACL, "
        "answer/tool gating, eval review, monitoring, and evidence hardening as independent phases."
    ),
    "support_impersonation": (
        "Plan support impersonation break-glass access with approved ticket, customer consent, supervisor approval, "
        "MFA, PII masking, tenant isolation, audit, revoke, expiry, and monitoring."
    ),
    "search_index": (
        "Plan knowledge-base full-text search index consistency with create/update/delete incremental sync, tenant ACL "
        "and permission revocation negatives, deleted-document negative search, idempotent reindex/backfill, cursor "
        "recovery, lag alerts, stable pagination/sort, audit, retry/DLQ, and local governance."
    ),
    "conflict_resolution": (
        "Plan collaborative document editing conflict resolution with two users editing the same paragraph, optimistic "
        "locking, safe merge or reject, offline replay idempotency, permission overwrite negatives, audit, monitoring, "
        "and last-write-wins blockers."
    ),
    "support_ticket_sla": (
        "Plan support ticket triage and SLA escalation with email/API import dedupe, queue lifecycle, agent claim/assign/"
        "priority/status permissions, SLA breach escalation, manager queue health, notification suppression, audit notes, "
        "tenant isolation, PII redaction, monitoring, and Kanban-only blockers."
    ),
    "subscription_entitlement_billing": (
        "Plan B2B SaaS subscription upgrade/downgrade entitlement activation with proration, credit memo, invoice totals, "
        "provider webhook replay, duplicate-click idempotency, team-member entitlement propagation, quota history, permission "
        "and tenant negatives, audit, rollback, monitoring, and checkout-success-only blockers."
    ),
    "dsar_data_export": (
        "Plan GDPR/CCPA DSAR data export with subject access request identity verification, user/admin/API permissions, "
        "profile/billing/orders/messages/attachments/audit metadata scope, cross-user and cross-tenant negatives, redaction, "
        "legal hold/retention exceptions, async retry/cancel/timeout, encrypted signed URL expiry, download audit, notification "
        "dedupe, rate limits, monitoring, and CSV-only blockers."
    ),
}


SPECIALIZED_WORKFLOW_SPEC_MARKERS = {
    "kyc_aml": "KYC/KYB and AML sanctions screening governance loop",
    "key_rotation": "API key / service account secret rotation lifecycle loop",
    "payment_webhook": "payment provider webhook / ledger governance loop",
    "identity_sso": "enterprise SAML/OIDC SSO / provisioning loop",
    "authorization_policy": "authorization policy consistency loop",
    "prompt_asset": "fixed system/developer prompt asset ownership loop",
    "data_residency": "EU/US data residency / regional isolation loop",
    "notification": "Notification Subscription Deliverability Workflow Notes",
    "analytics_experiment": "Analytics Experiment Instrumentation Workflow Notes",
    "rag_long_chain": "Long-Chain Workflow Notes",
    "support_impersonation": "support impersonation / break-glass admin access governance loop",
    "search_index": "Search Index Consistency Workflow Notes",
    "conflict_resolution": "Collaborative Conflict Resolution Workflow Notes",
    "support_ticket_sla": "Support Ticket SLA Workflow Notes",
    "subscription_entitlement_billing": "Subscription Entitlement Billing Workflow Notes",
    "dsar_data_export": "DSAR Data Export Workflow Notes",
}


def test_fake_alignment_fixtures_keep_payload_data_and_bundle_base_dedicated() -> None:
    (
        payloads_source,
        preconfirmation_source,
        responses_source,
        readiness_responses_source,
        base_bundle_source,
        bundle_variants_source,
        task_anchor_source,
        task_anchors_source,
        task_projection_source,
        task_projection_scope_source,
        readiness_source,
        contracts_source,
        service_boundaries_source,
    ) = (
        loopora_source("executor_alignment_payloads.py"),
        loopora_source("executor_alignment_preconfirmation_payloads.py"),
        loopora_source("executor_alignment_responses.py"),
        loopora_source("executor_alignment_readiness_responses.py"),
        loopora_source("executor_alignment_bundle_base_fixture.py"),
        loopora_source("executor_alignment_bundle_fixtures.py"),
        loopora_source("executor_alignment_bundle_task_anchor.py"),
        loopora_source("executor_alignment_task_anchors.py"),
        loopora_source("executor_alignment_task_projection.py"),
        loopora_source("executor_alignment_task_projection_scope.py"),
        loopora_source("executor_alignment_readiness_payloads.py"),
        design_contracts_source(),
        (Path(__file__).resolve().parents[3] / "design" / "service-boundaries.md").read_text(encoding="utf-8"),
    )

    _assert_bundle_scenario_fixture_asset_boundary(payloads_source)
    assert "from loopora.executor_alignment_task_anchors import" in payloads_source
    assert "def alignment_task_text_from_prompt" in task_anchors_source
    assert "def alignment_task_anchor_from_user_message" in task_anchors_source
    assert "ALIGNMENT_SESSION_TRANSCRIPT_BLOCK_RE" in task_anchors_source
    assert "ALIGNMENT_PROMPT_USER_CONTENT_RE" in task_anchors_source
    assert "def _alignment_user_messages_from_prompt" not in payloads_source
    assert "def _alignment_prompt_transcript" not in payloads_source
    assert "def _alignment_strip_mixed_confirmation_adjustment_prefix" not in payloads_source
    assert "from loopora.executor_alignment_readiness_payloads import" in payloads_source
    _assert_readiness_issue_fixture_asset_boundary(payloads_source, readiness_source)
    assert "from loopora.executor_alignment_preconfirmation_payloads import" in payloads_source
    assert "def alignment_preconfirmation_payload_for_scenario" in preconfirmation_source
    assert "def _alignment_preconfirmation_scenario_payload" in preconfirmation_source
    _assert_preconfirmation_fixture_asset_boundary(preconfirmation_source)
    assert "def _alignment_preconfirmation_scenario_payload" not in payloads_source
    assert "from loopora.executor_alignment_readiness_responses import" in responses_source
    assert "def alignment_readiness_evidence" in readiness_responses_source
    assert "def alignment_improvement_readiness_evidence" in readiness_responses_source
    assert "def alignment_readiness_evidence" not in responses_source
    assert "from loopora.executor_alignment_agreement_responses import" in responses_source
    assert "from loopora.executor_alignment_agreement_responses import" in preconfirmation_source
    _assert_static_bundle_base_boundaries()
    _assert_task_projection_scope_boundary(
        task_projection_source,
        task_projection_scope_source,
        service_boundaries_source,
    )
    assert "from loopora.executor_alignment_task_projection import" in task_anchor_source
    _assert_static_bundle_variant_asset_boundary(contracts_source, service_boundaries_source)
    for module_name in (
        "executor_alignment_bundle_localized_variants.py",
        "executor_alignment_bundle_improvement_variants.py",
        "executor_alignment_bundle_refund_variants.py",
        "executor_alignment_bundle_task_anchor.py",
        "executor_alignment_bundle_invalid_variants.py",
    ):
        import_name = module_name.removesuffix(".py")
        assert f"from loopora.{import_name} import" in bundle_variants_source
    for module_name in (
        "executor_alignment_bundle_localized_variants.py",
        "executor_alignment_bundle_localized_assets.py",
        "executor_alignment_bundle_variant_assets.py",
        "executor_alignment_bundle_improvement_assets.py",
        "executor_alignment_bundle_improvement_variants.py",
        "executor_alignment_bundle_refund_assets.py",
        "executor_alignment_bundle_refund_variants.py",
        "executor_alignment_bundle_task_anchor.py",
        "executor_alignment_bundle_specialized_shell.py",
        "executor_alignment_bundle_invalid_variants.py",
    ):
        assert module_name in contracts_source
        assert module_name in service_boundaries_source
    assert "from loopora.executor_alignment_bundle_specialized_shell import" in task_anchor_source
    assert "base-bundle.yml" in base_bundle_source
    assert "executor_alignment_agreement_responses.py" in contracts_source
    assert "executor_alignment_agreement_refund_responses.py" in contracts_source
    assert "executor_alignment_agreement_predicates.py" in contracts_source
    assert "executor_alignment_agreement_task_responses.py" in contracts_source
    assert "improvement-bundle-fixtures.yml" in contracts_source
    assert "improvement-bundle-fixtures.yml" in service_boundaries_source
    assert "refund-bundle-fixtures.yml" in contracts_source
    assert "refund-bundle-fixtures.yml" in service_boundaries_source
    assert "executor_alignment_preconfirmation_payloads.py" in contracts_source
    assert "executor_alignment_bundle_governance_fixture.py" in contracts_source
    assert "executor_alignment_task_projection.py" in contracts_source
    assert "workflow `inputs.evidence_query.verifies`" in contracts_source
    assert "independent evidence phases" in contracts_source


def _assert_task_projection_scope_boundary(
    task_projection_source: str,
    task_projection_scope_source: str,
    service_boundaries_source: str,
) -> None:
    assert "def alignment_task_domain_projection" in task_projection_source
    assert "from loopora.executor_alignment_task_projection_scope import" in task_projection_source
    assert "def projection_scoped_labels" in task_projection_scope_source
    assert "PROJECTION_LABEL_ANCHOR_PATTERNS" in task_projection_scope_source
    assert "executor_alignment_task_projection_scope.py" in service_boundaries_source
    for marker in (
        "PROJECTION_LABEL_ANCHOR_PATTERNS",
        "def _projection_scoped_labels",
        "def _projection_filter_primary_domain_noise",
        "def _projection_is_dsar_data_export_task",
        "def _projection_is_subscription_entitlement_billing_task",
        "def _projection_is_prompt_asset_ownership_task",
    ):
        assert marker not in task_projection_source


def _assert_static_bundle_base_boundaries() -> None:
    agreement_responses_source = loopora_source("executor_alignment_agreement_responses.py")
    base_bundle_source = loopora_source("executor_alignment_bundle_base_fixture.py")
    bundle_variants_source = loopora_source("executor_alignment_bundle_fixtures.py")
    governance_bundle_source = loopora_source("executor_alignment_bundle_governance_fixture.py")
    localized_variants_source = loopora_source("executor_alignment_bundle_localized_variants.py")
    responses_source = loopora_source("executor_alignment_responses.py")
    contracts_source = design_contracts_source()
    service_boundaries_source = (Path(__file__).resolve().parents[3] / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    for marker in (
        "def alignment_agreement_response",
        "def alignment_improvement_agreement_response",
        "def alignment_refund_agreement_response",
    ):
        assert marker in agreement_responses_source
        assert marker not in responses_source
    assert "from loopora.executor_alignment_bundle_base_fixture import" in bundle_variants_source
    assert "from loopora.executor_alignment_bundle_governance_fixture import" in base_bundle_source
    assert "from loopora.executor_alignment_bundle_governance_fixture import" in localized_variants_source
    assert "from loopora.executor_alignment_bundle_localized_assets import" in localized_variants_source
    assert "def alignment_bundle_yaml" in base_bundle_source
    assert "def alignment_bundle_governance_sentence" in governance_bundle_source
    assert "def alignment_bundle_governance_role_snippet" in governance_bundle_source
    assert "def _governance_markers_for_workdir" in governance_bundle_source
    assert "def alignment_bundle_governance_sentence" not in base_bundle_source
    assert "def alignment_bundle_governance_role_snippet" not in base_bundle_source
    assert "def alignment_chinese_bundle_yaml" not in base_bundle_source
    assert "def alignment_chinese_bundle_yaml" in localized_variants_source
    for snippet in (
        "将工作协议投影到 spec",
        "谨慎构建聚焦 starter slice",
    ):
        assert snippet not in localized_variants_source
    for artifact_name in (
        "executor_alignment_bundle_localized_assets.py",
        "localized-base-bundle-overrides.yml",
    ):
        assert artifact_name in contracts_source
        assert artifact_name in service_boundaries_source


def _assert_static_bundle_variant_asset_boundary(contracts_source: str, service_boundaries_source: str) -> None:
    improvement_variants_source = loopora_source("executor_alignment_bundle_improvement_variants.py")
    improvement_assets_source = loopora_source("executor_alignment_bundle_improvement_assets.py")
    refund_variants_source = loopora_source("executor_alignment_bundle_refund_variants.py")
    refund_assets_source = loopora_source("executor_alignment_bundle_refund_assets.py")
    variant_assets_source = loopora_source("executor_alignment_bundle_variant_assets.py")

    assert "from loopora.executor_alignment_bundle_improvement_assets import" in improvement_variants_source
    assert "from loopora.executor_alignment_bundle_refund_assets import" in refund_variants_source
    assert "from loopora.executor_alignment_bundle_variant_assets import" in improvement_assets_source
    assert "from loopora.executor_alignment_bundle_variant_assets import" in refund_assets_source
    assert "improvement-bundle-fixtures.yml" in improvement_assets_source
    assert "refund-bundle-fixtures.yml" in refund_assets_source
    assert "def apply_alignment_bundle_variant_fixture" in variant_assets_source
    for snippet in (
        "修订来源 Search Loop",
        "复杂度只是移动到另一个阶段",
        "search-refactor-improvement-long-chain",
    ):
        assert snippet not in improvement_variants_source
    for snippet in (
        "Ship a governed refund self-service path",
        "为退款用户、授权客户管理员、客服和财务交付受治理的退款自助路径",
        "refund_repair_review",
    ):
        assert snippet not in refund_variants_source
    for artifact_name in (
        "executor_alignment_bundle_variant_assets.py",
        "executor_alignment_bundle_improvement_assets.py",
        "executor_alignment_bundle_refund_assets.py",
        "improvement-bundle-fixtures.yml",
        "refund-bundle-fixtures.yml",
    ):
        assert artifact_name in contracts_source
        assert artifact_name in service_boundaries_source


def _assert_bundle_scenario_fixture_asset_boundary(payloads_source: str) -> None:
    bundle_scenario_fixtures_asset = (
        Path(__file__).resolve().parents[3] / "src" / "loopora" / "assets" / "alignment" / "bundle-scenario-fixtures.json"
    ).read_text(encoding="utf-8")
    assert "bundle-scenario-fixtures.json" in payloads_source
    assert "alignment_invalid" in bundle_scenario_fixtures_asset
    assert "alignment_refund_agreement_repair_bundle" in bundle_scenario_fixtures_asset
    assert "我先给出一个故意不完整的 bundle。" in bundle_scenario_fixtures_asset
    assert "I prepared a refund governance Loopora bundle with a Guide repair pass." in bundle_scenario_fixtures_asset
    assert "我先给出一个故意不完整的 bundle。" not in payloads_source
    assert "I prepared a refund governance Loopora bundle with a Guide repair pass." not in payloads_source
    assert "alignment_invalid" not in payloads_source
    assert "alignment_refund_agreement_repair_bundle" not in payloads_source


def _assert_readiness_issue_fixture_asset_boundary(payloads_source: str, readiness_source: str) -> None:
    readiness_issue_fixtures_asset = (
        Path(__file__).resolve().parents[3] / "src" / "loopora" / "assets" / "alignment" / "readiness-issue-fixtures.json"
    ).read_text(encoding="utf-8")
    assert "def alignment_readiness_issue_for_scenario" in readiness_source
    assert "readiness-issue-fixtures.json" in readiness_source
    assert "alignment_vague_loop_fit_readiness_evidence" in readiness_issue_fixtures_asset
    assert "alignment_vague_loop_fit_readiness_evidence" not in readiness_source
    assert "This is a complex and important task with many parts to handle well." in readiness_issue_fixtures_asset
    assert "This is a complex and important task with many parts to handle well." not in readiness_source
    assert "alignment_vague_loop_fit_readiness_evidence" not in payloads_source


def _assert_preconfirmation_fixture_asset_boundary(preconfirmation_source: str) -> None:
    preconfirmation_fixtures_asset = (
        Path(__file__).resolve().parents[3] / "src" / "loopora" / "assets" / "alignment" / "preconfirmation-scenario-fixtures.json"
    ).read_text(encoding="utf-8")
    assert "preconfirmation-scenario-fixtures.json" in preconfirmation_source
    assert "alignment_question" in preconfirmation_fixtures_asset
    assert "我建议先按" in preconfirmation_fixtures_asset
    assert "我建议先按" not in preconfirmation_source
    assert "alignment_question" not in preconfirmation_source


def test_fake_alignment_agreement_predicates_have_dedicated_boundary() -> None:
    agreement_responses_source = loopora_source("executor_alignment_agreement_responses.py")
    agreement_task_dispatch_source = loopora_source("executor_alignment_agreement_task_dispatch.py")
    agreement_task_dispatch_commercial_source = loopora_source("executor_alignment_agreement_task_dispatch_commercial.py")
    agreement_task_dispatch_data_source = loopora_source("executor_alignment_agreement_task_dispatch_data.py")
    agreement_task_dispatch_operations_source = loopora_source("executor_alignment_agreement_task_dispatch_operations.py")
    agreement_task_dispatch_product_source = loopora_source("executor_alignment_agreement_task_dispatch_product.py")
    agreement_task_dispatch_trust_source = loopora_source("executor_alignment_agreement_task_dispatch_trust.py")
    agreement_task_responses_source = loopora_source("executor_alignment_agreement_task_responses.py")
    agreement_predicates_source = loopora_source("executor_alignment_agreement_predicates.py")
    task_predicates_source = loopora_source("executor_alignment_task_predicates.py")
    product_task_predicates_source = loopora_source("executor_alignment_task_predicates_product.py")
    product_search_ai_task_predicates_source = loopora_source("executor_alignment_task_predicates_product_search_ai.py")
    commercial_task_predicates_source = loopora_source("executor_alignment_task_predicates_commercial.py")
    commercial_payments_task_predicates_source = loopora_source("executor_alignment_task_predicates_commercial_payments.py")
    contracts_source = design_contracts_source()
    service_boundaries_source = (Path(__file__).resolve().parents[3] / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.executor_alignment_agreement_predicates import" not in agreement_task_dispatch_source
    for dispatch_body_source in (
        agreement_task_dispatch_commercial_source,
        agreement_task_dispatch_data_source,
        agreement_task_dispatch_operations_source,
        agreement_task_dispatch_product_source,
        agreement_task_dispatch_trust_source,
    ):
        assert "from loopora.executor_alignment_agreement_predicates import" in dispatch_body_source
    assert "from loopora import executor_alignment_task_predicates as _task_predicates" in agreement_predicates_source
    assert "from loopora.executor_alignment_agreement_predicates import" not in agreement_responses_source
    assert "from loopora.executor_alignment_agreement_predicates import" not in agreement_task_responses_source
    for marker in (
        "def is_search_index_consistency_task",
        "def is_rag_long_chain_task",
    ):
        assert marker in product_search_ai_task_predicates_source
        assert marker not in product_task_predicates_source
        assert marker not in task_predicates_source
        assert marker not in agreement_task_dispatch_source
        assert marker not in agreement_task_responses_source
        assert marker not in agreement_responses_source
    assert "def is_payment_webhook_ledger_task" in commercial_payments_task_predicates_source
    assert "def is_payment_webhook_ledger_task" not in commercial_task_predicates_source
    assert "def is_payment_webhook_ledger_task" not in task_predicates_source
    for marker in (
        "_agreement_is_search_index_consistency_task = _task_predicates.is_search_index_consistency_task",
        "_agreement_is_rag_long_chain_task = _task_predicates.is_rag_long_chain_task",
        "_agreement_is_payment_webhook_ledger_task = _task_predicates.is_payment_webhook_ledger_task",
    ):
        assert marker in agreement_predicates_source
    assert "executor_alignment_agreement_predicates.py" in contracts_source
    assert "executor_alignment_agreement_task_dispatch_commercial.py" in contracts_source
    assert "executor_alignment_agreement_task_dispatch_product.py" in contracts_source
    assert "executor_alignment_task_predicates.py" in contracts_source
    assert "executor_alignment_task_predicates_product.py" in contracts_source
    assert "executor_alignment_task_predicates_product_search_ai.py" in contracts_source
    assert "executor_alignment_task_predicates_commercial.py" in contracts_source
    assert "executor_alignment_task_predicates_commercial_payments.py" in contracts_source
    assert "executor_alignment_agreement_predicates.py" in service_boundaries_source
    assert "executor_alignment_agreement_task_dispatch_commercial.py" in service_boundaries_source
    assert "executor_alignment_agreement_task_dispatch_product.py" in service_boundaries_source
    assert "executor_alignment_task_predicates.py" in service_boundaries_source
    assert "executor_alignment_task_predicates_product.py" in service_boundaries_source
    assert "executor_alignment_task_predicates_product_search_ai.py" in service_boundaries_source
    assert "executor_alignment_task_predicates_commercial.py" in service_boundaries_source
    assert "executor_alignment_task_predicates_commercial_payments.py" in service_boundaries_source


def test_fake_alignment_task_predicates_are_shared_across_bundle_and_agreement() -> None:
    from loopora import executor_alignment_agreement_predicates as agreement_predicates
    from loopora import executor_alignment_bundle_task_predicates as bundle_predicates

    shared_pairs = (
        ("_is_rag_long_chain_task", "_agreement_is_rag_long_chain_task"),
        ("_is_search_index_consistency_task", "_agreement_is_search_index_consistency_task"),
        ("_is_payment_webhook_ledger_task", "_agreement_is_payment_webhook_ledger_task"),
        ("_is_payout_settlement_reconciliation_task", "_agreement_is_payout_settlement_reconciliation_task"),
    )
    for bundle_name, agreement_name in shared_pairs:
        assert getattr(bundle_predicates, bundle_name) is getattr(agreement_predicates, agreement_name)

    rag_task = (
        "Plan RAG multiple evidence rounds with document ingestion, retrieval ACL, answer/tool gating, "
        "eval review, monitoring, source citations, prompt injection negatives, PII redaction, and fallback proof."
    )
    kyc_task = "Plan KYC/KYB sanctions screening with provider webhook replay, payout hold, privacy, and monitoring."
    inventory_task = "Plan inventory reservation consistency with SKU checkout oversell negatives and reservation expiry."

    assert bundle_predicates._is_rag_long_chain_task(rag_task)
    assert not bundle_predicates._is_search_index_consistency_task(rag_task)
    assert not agreement_predicates._agreement_is_search_index_consistency_task(rag_task)
    assert not bundle_predicates._is_payment_webhook_ledger_task(kyc_task)
    assert not agreement_predicates._agreement_is_payment_webhook_ledger_task(kyc_task)
    assert not bundle_predicates._is_payout_settlement_reconciliation_task(inventory_task)
    assert not agreement_predicates._agreement_is_payout_settlement_reconciliation_task(inventory_task)


def test_fake_alignment_agreement_task_dispatch_has_dedicated_boundary() -> None:
    sources = _agreement_response_boundary_sources()

    _assert_agreement_task_dispatch_boundary(sources)
    _assert_agreement_task_response_domain_boundaries(sources)
    _assert_agreement_task_response_design_inventory(sources)


def test_fake_alignment_bundle_task_routing_has_dedicated_boundary() -> None:
    sources = _bundle_task_routing_boundary_sources()

    _assert_bundle_task_routing_dispatch_boundary(sources)
    _assert_bundle_task_routing_appender_boundary(sources)
    _assert_bundle_task_spec_scaffold_domain_boundaries(sources)
    _assert_bundle_task_routing_design_inventory(sources)


def test_fake_alignment_bundle_task_workflows_have_dedicated_boundary() -> None:
    sources = _task_workflow_boundary_sources()

    _assert_task_workflow_dispatch_boundary(sources)
    _assert_task_workflow_shape_boundaries(sources)
    _assert_task_workflow_prose_boundaries(sources)
    _assert_task_workflow_design_inventory(sources)


def test_short_data_governance_tasks_keep_primary_domain_routing() -> None:
    cases = (
        (
            "Plan database schema migration with expand-contract rollout, backfill, rollback, data consistency checks, audit, and monitoring.",
            "database-schema-migration-contract-parallel-backfill",
            "database schema migration / backfill",
            "feature-flag-rollout-contract-parallel-release",
        ),
        (
            "Plan CDC replication consistency with schema evolution, snapshot backfill, checkpoints, out-of-order events, reconciliation, lag alerts, replay, idempotency, and monitoring.",
            "cdc-replication-contract-parallel-consistency",
            "CDC replication consistency",
            "task-evidence-repair",
        ),
    )

    for task, expected_preset, agreement_marker, wrong_preset in cases:
        bundle = yaml.safe_load(
            alignment_task_anchored_repair_bundle_yaml(
                "/tmp/loopora-data-governance-routing",
                task,
                prefers_chinese=False,
            )
        )
        agreement = alignment_task_anchored_agreement_response(task, prefers_chinese=False)

        assert bundle["workflow"]["preset"] == expected_preset
        assert bundle["workflow"]["preset"] != wrong_preset
        assert agreement_marker in agreement["assistant_message"]
        assert agreement["readiness_evidence"]["task_scope"]


def test_fake_alignment_bundle_task_roles_have_dedicated_boundary() -> None:
    bundle_variants_source = loopora_source("executor_alignment_bundle_fixtures.py")
    improvement_variants_source = loopora_source("executor_alignment_bundle_improvement_variants.py")
    refund_variants_source = loopora_source("executor_alignment_bundle_refund_variants.py")
    task_anchor_source = loopora_source("executor_alignment_bundle_task_anchor.py")
    bundle_task_roles_source = loopora_source("executor_alignment_bundle_task_roles.py")
    bundle_task_workflows_source = loopora_source("executor_alignment_bundle_task_workflows.py")
    contracts_source = design_contracts_source()
    service_boundaries_source = (Path(__file__).resolve().parents[3] / "design" / "service-boundaries.md").read_text(encoding="utf-8")

    assert "from loopora.executor_alignment_bundle_task_roles import" not in bundle_variants_source
    for caller_source in (improvement_variants_source, refund_variants_source, task_anchor_source):
        assert "from loopora.executor_alignment_bundle_task_roles import" in caller_source
    assert "from loopora.executor_alignment_bundle_task_predicates import" in bundle_task_roles_source
    assert "from loopora.executor_alignment_bundle_task_routing import" not in bundle_task_roles_source
    for marker in (
        "def _replace_task_anchored_roles",
        "class TaskRoleFixtureReplacement",
        "TASK_ROLE_FIXTURE_REPLACERS",
        "def _apply_search_refactor_improvement_roles",
        "def _apply_refund_repair_roles",
        "def _replace_task_role_definitions_from_asset",
        "def _task_role_prompt_markdown",
        "def _rag_long_chain_governance_prompt",
        "def _task_role_governance_prompts",
    ):
        assert marker in bundle_task_roles_source
        assert marker not in bundle_variants_source
    for obsolete_bridge_marker in (
        "def _task_anchored_role_replacers",
        "def _replace_data_residency_task_roles",
        "def _replace_payment_webhook_ledger_task_roles",
        "def _replace_rag_long_chain_task_roles",
    ):
        assert obsolete_bridge_marker not in bundle_task_roles_source
    for route_marker in (
        'TaskRoleFixtureReplacement(_is_data_residency_task, "data_residency")',
        'TaskRoleFixtureReplacement(_is_payment_webhook_ledger_task, "payment_webhook_ledger")',
        'TaskRoleFixtureReplacement(_is_rag_long_chain_task, "rag_long_chain")',
    ):
        assert route_marker in bundle_task_roles_source
    assert "def _rag_long_chain_governance_prompt" not in bundle_task_workflows_source
    assert "TASK_ROLE_FIXTURE_REPLACERS" in contracts_source
    assert "module-level predicate-to-fixture role routing" in service_boundaries_source
    assert "executor_alignment_bundle_task_roles.py" in contracts_source
    assert "executor_alignment_bundle_task_roles.py" in service_boundaries_source


def test_fake_alignment_agreement_evidence_has_dedicated_boundary() -> None:
    sources = _agreement_response_boundary_sources()
    sources["evidence"] = loopora_source("executor_alignment_agreement_evidence.py")
    agreement_readiness_asset_text = (
        Path(__file__).resolve().parents[3] / "src" / "loopora" / "assets" / "alignment" / "agreement-readiness-evidence.json"
    ).read_text(encoding="utf-8")
    agreement_readiness_asset = json.loads(agreement_readiness_asset_text)

    _assert_agreement_evidence_import_boundary(sources)
    _assert_agreement_readiness_asset_boundary(sources, agreement_readiness_asset_text, agreement_readiness_asset)
    _assert_agreement_evidence_design_inventory(sources)


def test_base_alignment_bundle_role_prompt_bodies_live_in_asset() -> None:
    base_bundle_source = loopora_source("executor_alignment_bundle_base_fixture.py")
    bundle_variants_source = loopora_source("executor_alignment_bundle_fixtures.py")
    contracts_source = design_contracts_source()
    base_bundle_asset = (Path(__file__).resolve().parents[3] / "src" / "loopora" / "assets" / "alignment" / "base-bundle.yml").read_text(encoding="utf-8")

    assert "base-bundle.yml" in contracts_source
    for snippet in (
        "Build the focused starter slice carefully and keep the repo coherent.",
        "Inspect the Builder handoff against Done When, Guardrails, Fake Done",
        "Decide from direct evidence and do not accept vague completion claims.",
    ):
        assert snippet in base_bundle_asset
        assert snippet not in base_bundle_source
        assert snippet not in bundle_variants_source


def test_task_specific_role_fixture_prompt_bodies_live_in_asset() -> None:
    bundle_variants_source = loopora_source("executor_alignment_bundle_fixtures.py")
    bundle_task_roles_source = loopora_source("executor_alignment_bundle_task_roles.py")
    contracts_source = design_contracts_source()
    task_role_fixture_asset = (Path(__file__).resolve().parents[3] / "src" / "loopora" / "assets" / "alignment" / "task-role-fixtures.json").read_text(
        encoding="utf-8"
    )

    assert "task-role-fixtures.json" in bundle_task_roles_source
    assert "task-role-fixtures.json" in contracts_source
    assert "role_specs = (" not in bundle_variants_source
    assert "role_specs = (" not in bundle_task_roles_source
    assert "def _replace_spanish_task_anchored_roles" not in bundle_variants_source
    assert "def _replace_spanish_task_anchored_roles" not in bundle_task_roles_source
    for snippet in (
        "Build the smallest real loop for the task anchor.",
        "Build the narrow refund self-service path carefully.",
        "Inspect the Builder handoff against refund authorization",
        "Read the Refund Repair Guide handoff before editing.",
        "Freeze the source Search Loop baseline",
        "Disprove complexity only moved elsewhere",
        "Read-only freeze the EU/US data-plane inventory",
        "Read-only freeze approval, consent, reason",
        "Read-only freeze provider event schemas",
        "Read-only freeze fixed system/developer prompt surfaces",
        "Freeze document-version, source-span, retrieval ACL",
        "Read-only freeze default-off behavior, cohort targeting",
        "实现前只读固定 default-off",
        "Build price-update invalidation across PDP/cart/checkout/API/CDN/Redis/read-model",
        "实现前只读固定 price surfaces",
        "Read-only freeze document event schema",
        "Verify tenant ACL changes",
        "Read-only freeze two-user same-paragraph edit fixtures",
        "Verify unauthorized overwrite rejection",
        "Read-only freeze email/API import",
        "Build ticket import, dedupe/merge",
        "Verify email/API import dedupe",
        "Verify claim/assign/priority/status permission negatives",
        "Read-only freeze DSAR / subject access request intake",
        "Build the DSAR export path from the contract handoff",
        "Verify DSAR scope coverage across profile",
        "Verify request authentication and permission negatives",
        "Read-only freeze subscription plan-change lifecycle",
        "Build subscription upgrade/downgrade and entitlement activation",
        "Verify entitlement state after plan changes",
        "Verify billing and provider reconciliation for subscription changes",
        "Read-only freeze CSV field mapping",
        "Build the import pipeline from the contract handoff",
        "Verify PII redaction in logs and row errors",
    ):
        assert snippet in task_role_fixture_asset
        assert snippet not in bundle_variants_source
        assert snippet not in bundle_task_roles_source


def test_generic_task_anchor_role_fixtures_match_workflow_role_refs(sample_workdir: Path) -> None:
    bundle = yaml.safe_load(
        alignment_task_anchored_repair_bundle_yaml(
            str(sample_workdir.resolve()),
            "Build a focused internal dashboard with audit evidence.",
            prefers_chinese=False,
        )
    )

    expected_role_keys = [
        "task-builder",
        "task-inspector",
        "task-repair-guide",
        "task-repair-builder",
        "task-gatekeeper",
    ]
    assert [role["key"] for role in bundle["role_definitions"]] == expected_role_keys
    assert [role["role_definition_key"] for role in bundle["workflow"]["roles"]] == expected_role_keys
    assert bundle["workflow"]["steps"][-1]["role_id"] == "task_gatekeeper"
    assert "Task anchor: Build a focused internal dashboard with audit evidence." in bundle["role_definitions"][0]["prompt_markdown"]


def test_specialized_workflows_do_not_inherit_generic_repair_shell(sample_workdir: Path) -> None:
    generic_repair_tokens = (
        "Task Evidence Repair Loop",
        "Repair Builder",
        "Guide 只把弱证据",
        "task-evidence-repair",
        "Builder -> Inspector -> Guide",
        "task-specific evidence workflow",
        "task-specific proof focuses",
        "These shallow states cannot pass",
    )
    for task_name, task_text in SPECIALIZED_WORKFLOW_TASKS.items():
        bundle_text = alignment_task_anchored_repair_bundle_yaml(
            str(sample_workdir.resolve()),
            task_text,
            prefers_chinese=False,
            display_language="en",
        )
        bundle = yaml.safe_load(bundle_text)

        assert bundle["workflow"]["preset"] != "task-evidence-repair", task_name
        assert SPECIALIZED_WORKFLOW_SPEC_MARKERS[task_name] in bundle["spec"]["markdown"], task_name
        for token in generic_repair_tokens:
            assert token not in bundle_text, task_name


def test_dsar_projection_keeps_secondary_domain_noise_out() -> None:
    projection = alignment_task_domain_projection(
        "我要给企业客户做 GDPR/CCPA DSAR data export。必须覆盖 profile、billing、orders、messages、attachments、audit metadata，"
        "排除其他 user/tenant，处理 redaction、legal hold/retention exceptions、async retry/cancel/timeout、signed URL expiry、download audit、notification dedupe 和 rate limit。",
        display_language="zh",
    )

    assert "DSAR 请求身份验证" in projection.success_focus
    assert projection.evidence_verifies == [
        "task_anchor",
        "negative_evidence",
        "audit_reconciliation",
        "fake_done",
        "data-export",
    ]
    projection_text = " ".join(
        [
            projection.success_focus,
            projection.fake_done_focus,
            projection.evidence_focus,
            " ".join(projection.evidence_verifies),
        ]
    )
    for unrelated in (
        "KYC",
        "key rotation",
        "file-upload",
        "quota-metering",
        "authorization-policy",
        "kyc-aml-screening",
    ):
        assert unrelated not in projection_text


def test_alignment_fake_bundle_keeps_runtime_judgment_surfaces_visible(sample_workdir: Path) -> None:
    bundle_text = alignment_bundle_yaml(str(sample_workdir.resolve()))

    assert "Execution Strategy, Judgment Tradeoffs, Local Governance, and Residual Risk" in bundle_text
    assert "sequencing drift, lowered tradeoffs, local-governance gaps" in bundle_text
    assert "prove the task contract, execution strategy, judgment tradeoffs, local governance when present" in bundle_text
    assert "Intermediate control points measure weak evidence and fake-done drift" in bundle_text
    assert "trigger a continue / correct / halt decision" in bundle_text
    assert "keep the required evidence target explicit" in bundle_text
    assert "Treat status-only checkpoints as insufficient" in bundle_text


def test_alignment_chinese_fake_bundle_does_not_trigger_loop_fit_contradiction(sample_workdir: Path) -> None:
    bundle = yaml.safe_load(alignment_chinese_bundle_yaml(str(sample_workdir.resolve())))

    assert not text_mentions_loop_fit_contradiction(alignment_bundle_visible_text(bundle))
