from __future__ import annotations

from pathlib import Path

from executor_architecture_test_support import design_contracts_source, loopora_source
from loopora.alignment_semantics import text_mentions_loop_fit_contradiction
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
        "Plan enterprise SAML/OIDC SSO with SCIM provisioning, tenant binding, forged assertion negatives, "
        "deprovisioning, role mapping, audit, and monitoring."
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
    payloads_source = loopora_source("executor_alignment_payloads.py")
    preconfirmation_source = loopora_source("executor_alignment_preconfirmation_payloads.py")
    responses_source = loopora_source("executor_alignment_responses.py")
    agreement_responses_source = loopora_source("executor_alignment_agreement_responses.py")
    readiness_responses_source = loopora_source("executor_alignment_readiness_responses.py")
    base_bundle_source = loopora_source("executor_alignment_bundle_base_fixture.py")
    governance_bundle_source = loopora_source("executor_alignment_bundle_governance_fixture.py")
    bundle_variants_source = loopora_source("executor_alignment_bundle_fixtures.py")
    task_projection_source = loopora_source("executor_alignment_task_projection.py")
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
    assert "def alignment_task_domain_projection" in task_projection_source
    assert "from loopora.executor_alignment_task_projection import" in bundle_variants_source
    assert "def _replace_rag_long_chain_task_workflow" in bundle_variants_source
    assert "rag-grounding-long-chain" in bundle_variants_source
    assert "def alignment_bundle_governance_sentence" not in base_bundle_source
    assert "def alignment_bundle_governance_role_snippet" not in base_bundle_source
    assert "def alignment_chinese_bundle_yaml" not in base_bundle_source
    assert "def alignment_chinese_bundle_yaml" in bundle_variants_source
    assert "base-bundle.yml" in base_bundle_source
    assert "executor_alignment_agreement_responses.py" in contracts_source
    assert "executor_alignment_preconfirmation_payloads.py" in contracts_source
    assert "executor_alignment_bundle_governance_fixture.py" in contracts_source
    assert "executor_alignment_task_projection.py" in contracts_source
    assert "workflow `inputs.evidence_query.verifies`" in contracts_source
    assert "independent evidence phases" in contracts_source


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
    contracts_source = design_contracts_source()
    task_role_fixture_asset = (Path(__file__).resolve().parents[3] / "src" / "loopora" / "assets" / "alignment" / "task-role-fixtures.json").read_text(
        encoding="utf-8"
    )

    assert "task-role-fixtures.json" in bundle_variants_source
    assert "task-role-fixtures.json" in contracts_source
    assert "role_specs = (" not in bundle_variants_source
    assert "def _replace_spanish_task_anchored_roles" not in bundle_variants_source
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
