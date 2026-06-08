from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from loopora.agent_adapter_entry_contracts import agent_plan_contract


def test_agent_plan_contract_keeps_agent_native_planning_interactive() -> None:
    contract = agent_plan_contract(
        adapter="codex",
        adapter_label="Codex",
        marker_source="codex_project_skill",
    )

    assert "`/loopora-plan` is an interactive alignment conversation, not a one-prompt compiler" in contract
    assert "form a working agreement, wait for explicit confirmation" in contract
    for category in (
        "notification / subscription-deliverability",
        "idempotency / duplicate-prevention",
        "migration / rollback-integrity",
        "compatibility / backward-compat",
        "evaluation / eval-set",
        "ai / rag-grounding-tool-safety",
        "access / tenant-isolation",
        "usage / quota-metering",
        "tax / calculation-compliance",
        "webhook / signature-replay-ordering",
        "billing / ledger-reconciliation",
        "billing / subscription-entitlement-proration",
        "payment / dispute-chargeback-lifecycle",
        "reporting / metric-reconciliation",
        "identity / sso-assertion",
        "locale / i18n",
    ):
        assert category in contract
    assert "Do not treat a detailed first prompt as confirmation" in contract
    assert "alignment inputs, not a confirmed working agreement" in contract
    assert "## Message Preservation" in contract
    assert "Use `--message` for the current task context, not a lossy title" in contract
    assert "do not compress away evidence modes, blockers, exception categories" in contract
    assert "Do not shrink those alignment inputs into a title-only `--message`" in contract
    assert "Use the message-only form while alignment, working-agreement confirmation, or Web review is still pending" in contract
    assert 'plan --workdir "$PWD" --message "<non-empty task context>" --entry-source codex_project_skill --json --compact-json' in contract
    assert "short task summary" not in contract
    assert "do not replace the interactive alignment path with a one-shot candidate-file path" in contract
    assert "same Agent context binding / alignment_session_id" in contract
    assert "appends to the existing planning conversation" in contract
    assert "do not author or repair a candidate file from that prompt until confirmation is explicit" in contract
    assert "Do not make a message-only plan call as the first planning attempt" not in contract
    assert "planning should author the Loop contract from current task context and managed references" not in contract
    assert "create the candidate plan file in step 3" not in contract


def test_agent_plan_contract_skeleton_matches_current_bundle_schema() -> None:
    contract = agent_plan_contract(
        adapter="codex",
        adapter_label="Codex",
        marker_source="codex_project_skill",
    )

    assert "Alignment or Web review:" in contract
    assert "Confirmed bundle or repair:" in contract
    assert 'plan --workdir "$PWD" --message "<non-empty task context>" --entry-source codex_project_skill --json --compact-json' in contract
    assert "# Success Surface\n    - ..." in contract
    assert "# Role Notes\n    ## Task Builder Notes" in contract
    assert 'on_pass: "continue"' in contract
    assert 'on_pass: "finish_run"' in contract
    assert "`# Role Notes` must use `## <Role Name> Notes` subheadings" in contract
    assert "Non-GateKeeper workflow steps must use `on_pass: \"continue\"`" in contract
    assert "`inputs.evidence_query` only accepts structured selector keys" in contract
    assert "metadata.name`, `loop.name`, role names, descriptions, prompt prose, and posture notes in the user's display language" in contract
    assert "evidence_query:\n          archetypes: [\"builder\"]\n          limit: 8" in contract
    assert "evidence_query:\n          archetypes: [\"builder\"]\n          limit: 8\n          text:" not in contract


def test_agent_native_design_keeps_plan_interactive() -> None:
    design = Path("design/contracts.md").read_text(encoding="utf-8")

    assert "`/loopora-plan` is an interactive alignment path" in design
    assert "message-only plan calls are the primary path while Loopora fit" in design
    assert "message-only continuation is scoped by the same Agent context binding" in design
    assert "append to that `alignment_session_id` instead of creating a new planning session" in design
    assert "`waiting_user` / `continue_alignment_dialogue` result is a hard stop for the host Agent" in design
    assert "host inference, workdir probes, Web scraping, default policy, or Agent preference must not answer" in design
    assert "A detailed first prompt is alignment input, not confirmation" in design
    assert "A pure confirmation reply is stage-control input rather than task-anchor text" in design
    assert "pure confirmation wording as task-anchor requirement" in design
    assert "Plan-stage guidance conducts interactive alignment from current task context and managed references" in design
    assert "Agent Native `/loopora-plan` managed authoring skeleton and Web alignment bundle guidance are schema guards" in design
    assert "Success Surface bullets" in design
    assert "Role Notes `## <Role Name> Notes` subheadings" in design
    assert 'non-GateKeeper `on_pass: "continue"`' in design
    assert "structured `inputs.evidence_query`" in design
    assert "should author a candidate file before the first compact plan command" not in design
    assert "message-only Web prefill as the primary plan path when a candidate file can be authored" not in design


def test_cli_agent_plan_support_ticket_rounds_use_parallel_sla_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-support-ticket-sla",
    }
    task_message = (
        "Plan a governed Loop for a support ticket triage and SLA escalation dashboard. Success cannot be just a Kanban "
        "page: tickets imported from email and API must dedupe, merge, and enqueue; agents must claim, assign, and change "
        "priority/status only with permissions; SLA clock boundary, pause/resume, breach escalation, and manager queue "
        "health reconciliation must be correct; customer and owner notifications must not duplicate; audit notes must be "
        "traceable; tenant isolation and PII redaction need negative evidence. Fake done is Kanban-only, manager dashboard "
        "only, queued/open status only, no email/API import dedupe, no permission negatives, no SLA breach proof, no "
        "notification suppression, no audit trail, no PII redaction, or skipped local governance."
    )

    first_summary = _invoke_support_ticket_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_support_ticket_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Support Ticket Contract Inspector freezing email/API import fixtures, dedupe/"
            "merge semantics, queue lifecycle state machine, claim/assign/priority/status permission matrix, SLA clock "
            "boundary, pause/resume behavior, breach escalation rules, manager queue health reconciliation, notification "
            "send/suppress dedupe logs, audit notes, tenant isolation, PII redaction, monitoring, and local governance. "
            "Ticket SLA Builder implements only after that handoff. Then run Ticket Lifecycle Inspector and Access "
            "Notification Audit Inspector in parallel: Ticket Lifecycle verifies import dedupe, state transitions, queue "
            "health, SLA clock boundaries, pause/resume, and breach escalation; Access Notification Audit verifies permission "
            "negatives, tenant isolation, notification send/suppress logs, audit notes, PII redaction, monitoring, and "
            "governance. GateKeeper must fail closed on Kanban-only, manager-dashboard-only, status-only, missing dedupe, "
            "missing lifecycle transitions, missing SLA boundary or breach escalation proof, missing permission or tenant "
            "negatives, missing notification suppression, missing audit/PII proof, missing monitoring, or skipped governance."
        ),
        env=env,
    )
    _assert_support_ticket_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_support_ticket_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this support ticket SLA contract-first parallel evidence direction.",
        env=env,
    )
    _assert_support_ticket_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _support_ticket_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_support_ticket_bundle(bundle_text)


def _invoke_support_ticket_plan_round(
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


def _assert_support_ticket_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Support Ticket Contract Inspector" in agreement_text
    assert "Ticket SLA Builder" in agreement_text
    assert "Ticket Lifecycle Inspector" in agreement_text
    assert "Access Notification Audit Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Notification Contract Inspector" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_support_ticket_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("support ticket", "SLA", "dedupe", "permission", "tenant", "notification", "audit", "PII"):
        assert term in ready_projection_text
    assert "Confirm; use this support ticket" not in ready_projection_text


def _support_ticket_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_support_ticket_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "support-ticket-contract-inspector",
        "ticket-sla-builder",
        "ticket-lifecycle-inspector",
        "access-notification-audit-inspector",
        "support-ticket-gatekeeper",
    ]
    assert workflow["preset"] == "support-ticket-contract-parallel-sla"
    assert [step["id"] for step in workflow["steps"]] == [
        "support_ticket_contract_inspection_step",
        "ticket_sla_builder_step",
        "ticket_lifecycle_inspection_step",
        "access_notification_audit_inspection_step",
        "support_ticket_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["support_ticket_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "support_ticket_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "support_ticket_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "support_ticket_contract_inspection_step",
        "ticket_sla_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "support_ticket_contract_inspection_step",
        "ticket_sla_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "support_ticket_contract_inspection_step",
        "ticket_sla_builder_step",
        "ticket_lifecycle_inspection_step",
        "access_notification_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "support-ticket-lifecycle",
        "sla-escalation",
        "idempotency",
        "queue-recovery",
        "permission-auth",
        "tenant-isolation",
        "message-delivery",
        "audit-log",
        "privacy-redaction",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Support Ticket SLA Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "notification-subscription-contract-parallel-deliverability" not in bundle_text
    assert "Notification Contract Inspector" not in bundle_text
    assert "Confirm; use this support ticket" not in bundle_text


def test_cli_agent_plan_subscription_entitlement_rounds_use_parallel_billing_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-subscription-entitlement",
    }
    task_message = (
        "我要做 B2B SaaS 的订阅套餐升级/降级和权益生效。客户可以从 Basic 升级到 Pro 或降级，必须正确处理 "
        "proration、发票/credit memo、试用期、宽限期、billing period 边界、provider webhook 延迟/重复/乱序、"
        "并发重复点击、幂等、团队成员权益开关、历史用量和 quota、权限/tenant 边界、审计、回滚和监控。"
        "不能只做一个按钮或只信 provider checkout success。成功证据要能证明账单金额、权益状态、"
        "发票/ledger/provider 对账、权限负向、重复请求、webhook replay 和降级延迟生效都对。"
    )

    first_summary = _invoke_subscription_entitlement_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_subscription_entitlement_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: use evidence-first contract-first workflow. Subscription Contract Inspector freezes "
            "plan-change lifecycle, upgrade immediate effect, downgrade next-cycle effect, proration, credit memo, invoice "
            "totals, trial/grace, billing period boundaries, provider checkout/webhook replay, duplicate-click idempotency, "
            "team-member entitlements, quota/history preservation, permission/tenant negatives, audit, rollback, monitoring, "
            "and governance. Entitlement Billing Builder implements only after that handoff. Then run Entitlement State "
            "Inspector and Billing Proration Reconciliation Inspector in parallel: Entitlement State verifies upgrade/"
            "downgrade timing, team propagation, feature access, quota/history, permissions, tenant negatives, audit and "
            "monitoring; Billing verifies proration, credit memo, invoice totals, ledger/provider reconciliation, webhook "
            "delay/replay/out-of-order, duplicate-click idempotency, billing boundary, rollback, monitoring and governance. "
            "GateKeeper must fail closed on button-only, checkout-success-only, provider-total-only, happy-path plan change, "
            "missing downgrade delay, missing proration/credit memo, missing entitlements, missing permissions, missing "
            "webhook replay/idempotency, missing reconciliation, missing rollback/monitoring, or skipped governance."
        ),
        env=env,
    )
    _assert_subscription_entitlement_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_subscription_entitlement_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this subscription entitlement contract-first parallel billing direction.",
        env=env,
    )
    _assert_subscription_entitlement_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _subscription_entitlement_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_subscription_entitlement_bundle(bundle_text)


def _invoke_subscription_entitlement_plan_round(
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


def _assert_subscription_entitlement_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Subscription Contract Inspector" in agreement_text
    assert "Entitlement Billing Builder" in agreement_text
    assert "Entitlement State Inspector" in agreement_text
    assert "Billing Proration Reconciliation Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Notification Contract Inspector" not in agreement_text
    assert "Campaign Email Builder" not in agreement_text
    assert "Quota Contract Inspector" not in agreement_text
    assert "Tax Contract Inspector" not in agreement_text
    assert "Payment Webhook Contract Inspector" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_subscription_entitlement_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("订阅", "权益", "proration", "credit memo", "发票", "provider", "回滚"):
        assert term in ready_projection_text
    assert "subscription filtering, deliverability" not in ready_projection_text
    assert "Confirm; use this subscription entitlement" not in ready_projection_text


def _subscription_entitlement_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_subscription_entitlement_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "subscription-contract-inspector",
        "entitlement-billing-builder",
        "entitlement-state-inspector",
        "billing-proration-reconciliation-inspector",
        "subscription-entitlement-gatekeeper",
    ]
    assert workflow["preset"] == "subscription-entitlement-contract-parallel-billing"
    assert [step["id"] for step in workflow["steps"]] == [
        "subscription_contract_inspection_step",
        "entitlement_billing_builder_step",
        "entitlement_state_inspection_step",
        "billing_proration_reconciliation_inspection_step",
        "subscription_entitlement_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["subscription_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "subscription_entitlement_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "subscription_entitlement_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "subscription_contract_inspection_step",
        "entitlement_billing_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "subscription_contract_inspection_step",
        "entitlement_billing_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "subscription_contract_inspection_step",
        "entitlement_billing_builder_step",
        "entitlement_state_inspection_step",
        "billing_proration_reconciliation_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "subscription-entitlement",
        "payment-refund-billing",
        "ledger-reconciliation",
        "provider-contract",
        "idempotency",
        "permission-auth",
        "tenant-isolation",
        "quota-metering",
        "audit-log",
        "monitoring",
        "migration-rollback",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Subscription Entitlement Billing Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "notification-subscription-contract-parallel-deliverability" not in bundle_text
    assert "Notification Contract Inspector" not in bundle_text
    assert "Campaign Email Builder" not in bundle_text
    assert "Confirm; use this subscription entitlement" not in bundle_text


def test_cli_agent_plan_dsar_export_rounds_use_privacy_export_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-dsar-export",
    }
    task_message = (
        "我要给企业客户做 GDPR/CCPA DSAR data export。成功不能只是一个 CSV 下载按钮；subject access request "
        "从用户、管理员或 API 发起后必须证明 identity verification 和 permissions；export scope 必须覆盖 profile、"
        "billing、orders、messages、attachments、audit-visible metadata，同时排除其他用户和其他 tenant；PII/secret "
        "redaction 与 legal hold/retention exceptions 必须正确；async export job 必须可 retry、cancel、timeout "
        "且保持 idempotent；encrypted files、short-lived signed URLs、expiry cleanup、download audit、notification "
        "dedupe、rate limits、monitoring 和 local governance 都需要证据。Fake done 是 CSV-only、download-button-only、"
        "dashboard-ready-only、missing scope coverage、missing tenant/user negatives、missing redaction、missing legal-hold "
        "exception、missing async lifecycle、missing encrypted expiring file、missing download audit、duplicate notifications、"
        "missing rate limit 或 skipped governance。"
    )

    first_summary = _invoke_dsar_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_dsar_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with DSAR Export Contract Inspector freezing subject request intake, identity "
            "verification, requester/admin/API permission matrix, export scope inventory, tenant/user exclusion negatives, "
            "PII/secret redaction, legal hold/retention exceptions, async export job lifecycle, encrypted delivery, signed "
            "URL expiry, expiry cleanup, download audit, notification dedupe, rate limits, monitoring, and local governance. "
            "Privacy Export Builder implements only after that handoff. Then run Export Scope Inspector and Access Retention "
            "Audit Inspector in parallel: Export Scope verifies profile/billing/orders/messages/attachments/audit-visible "
            "metadata coverage, format parity, partial failure, and cross-user/cross-tenant negatives; Access Retention Audit "
            "verifies auth/permission negatives, redaction, legal hold/retention exceptions, async retry/cancel/timeout, "
            "encrypted signed URL expiry, cleanup, download audit, notification dedupe, rate limits, monitoring, and governance. "
            "GateKeeper must fail closed on CSV-only, download-button-only, dashboard-ready-only, missing auth, missing scope, "
            "missing tenant/user negatives, missing redaction, missing retention exception, missing async lifecycle, missing "
            "encrypted expiring file, missing download audit, duplicate notifications, missing rate limit, missing monitoring, "
            "or skipped governance."
        ),
        env=env,
    )
    _assert_dsar_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_dsar_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this DSAR export contract-first parallel privacy direction.",
        env=env,
    )
    _assert_dsar_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _dsar_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_dsar_bundle(bundle_text)


def _invoke_dsar_plan_round(
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


def _assert_dsar_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "DSAR Export Contract Inspector" in agreement_text
    assert "Privacy Export Builder" in agreement_text
    assert "Export Scope Inspector" in agreement_text
    assert "Access Retention Audit Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "Notification Contract Inspector" not in agreement_text
    assert "Campaign Email Builder" not in agreement_text
    assert "Data Lifecycle Contract Inspector" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_dsar_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("DSAR", "data export", "permission", "tenant", "redaction", "retention", "signed URL", "download audit"):
        assert term in ready_projection_text
    assert "Confirm; use this DSAR" not in ready_projection_text


def _dsar_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_dsar_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "dsar-export-contract-inspector",
        "privacy-export-builder",
        "export-scope-inspector",
        "access-retention-audit-inspector",
        "dsar-export-gatekeeper",
    ]
    assert workflow["preset"] == "dsar-export-contract-parallel-privacy"
    assert [step["id"] for step in workflow["steps"]] == [
        "dsar_export_contract_inspection_step",
        "privacy_export_builder_step",
        "export_scope_inspection_step",
        "access_retention_audit_inspection_step",
        "dsar_export_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["dsar_export_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "dsar_export_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "dsar_export_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "dsar_export_contract_inspection_step",
        "privacy_export_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "dsar_export_contract_inspection_step",
        "privacy_export_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "dsar_export_contract_inspection_step",
        "privacy_export_builder_step",
        "export_scope_inspection_step",
        "access_retention_audit_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "data-export",
        "privacy-redaction",
        "permission-auth",
        "tenant-isolation",
        "deletion-retention",
        "async-job-lifecycle",
        "idempotency",
        "audit-log",
        "message-delivery",
        "rate-limit",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "DSAR Data Export Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "notification-subscription-contract-parallel-deliverability" not in bundle_text
    assert "Notification Contract Inspector" not in bundle_text
    assert "Confirm; use this DSAR" not in bundle_text
