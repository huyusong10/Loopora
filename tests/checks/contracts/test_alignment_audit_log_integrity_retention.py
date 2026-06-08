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
from loopora.executor_fake_payloads import alignment_bundle_yaml


AUDIT_TRAIL_TASK_TEXT = (
    "我要给管理员敏感操作做 compliance audit trail。成功必须证明 create/update/delete、permission change "
    "和 failed attempt 都写入 append-only audit log，actor、subject、tenant、request id、IP、user agent、"
    "before/after diff 和 reason code 完整，PII/token 已脱敏，timestamp 单调且能处理 clock skew，"
    "tamper-evident hash chain 或 WORM storage 能证明日志不可改，retention policy 和 legal hold 生效，"
    "SIEM/export 对账成功，访问控制和 tenant isolation 防止跨租户看日志，重试不会漏记或重复记，"
    "logging failure、stale exporter 和 gap in sequence 有监控告警；只有数据库表里有一行记录、"
    "console log 打出来或 UI history 显示一条操作必须阻断。"
)


def test_cli_agent_plan_audit_log_rounds_use_parallel_retention_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-audit-log-integrity-retention",
    }
    task_message = (
        "Plan a governed Loop for admin compliance audit trail integrity and retention. Success must prove "
        "create/update/delete, permission changes, and failed attempts write append-only audit log entries; actor, "
        "subject, tenant, request id, IP, user agent, before/after diff, reason code, timestamp, and sequence fields "
        "are complete; PII/tokens are redacted; timestamps are monotonic and handle clock skew; tamper-evident hash "
        "chain or WORM storage proves logs cannot be changed; retention policy and legal hold work; SIEM/export "
        "reconciliation succeeds; access control and tenant isolation prevent cross-tenant log reads; retries do not "
        "miss or duplicate entries; logging failure, stale exporter, and sequence gaps trigger monitoring alerts. "
        "Fake done is one database audit row, console log output, UI history showing an operation, audit reviewability "
        "only, no tamper negative, no retention/legal hold proof, no export reconciliation, no tenant negative, or "
        "treating monitoring as follow-up."
    )

    first_summary = _invoke_audit_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_audit_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Audit Contract Inspector freezing event matrix, required fields, "
            "redaction, append-only/hash-chain/WORM integrity, retention/legal hold, SIEM/export reconciliation, "
            "tenant access controls, retry no-miss/no-duplicate semantics, logging failure and sequence gap "
            "monitoring, migration/backward compatibility, and local governance. Audit Trail Builder implements only "
            "after that handoff. Then run Audit Integrity Inspector and Retention Export Inspector in parallel: Audit "
            "Integrity checks operation and failed-attempt fixtures, required fields, redaction, timestamp monotonicity "
            "and clock skew, tamper negatives, sequence gaps, retry idempotency, and tenant negative access; Retention "
            "Export checks retention policy, legal hold, WORM/hash-chain evidence, SIEM/export reconciliation, stale "
            "exporter/logging failure alerts, audit access permissions, migration compatibility, and governance. "
            "GateKeeper must fail closed on row-only, console-log-only, UI-history-only, reviewability-only, missing "
            "tamper negative, missing retention/legal hold, missing export reconciliation, missing tenant negative, "
            "missing redaction, missing retry proof, missing monitoring, or skipped local governance."
        ),
        env=env,
    )
    _assert_audit_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_audit_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this audit log integrity contract-first parallel retention direction.",
        env=env,
    )
    _assert_audit_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _audit_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_audit_bundle(bundle_text)


def _invoke_audit_plan_round(
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


def _assert_audit_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Audit Contract Inspector" in agreement_text
    assert "Audit Trail Builder" in agreement_text
    assert "Audit Integrity Inspector" in agreement_text
    assert "Retention Export Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "GDPR data deletion" not in agreement_text
    assert "Data Lifecycle Contract Inspector" not in agreement_text
    assert "Deletion Builder" not in agreement_text
    assert "Privacy Deletion Evidence Inspector" not in agreement_text
    assert "task-evidence-repair" not in agreement_text


def _assert_audit_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("audit", "tamper", "retention", "legal", "export", "tenant", "redaction", "monitoring"):
        assert term in ready_projection_text
    assert "Confirm; use this audit" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _audit_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_audit_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "audit-contract-inspector",
        "audit-trail-builder",
        "audit-integrity-inspector",
        "retention-export-inspector",
        "audit-compliance-gatekeeper",
    ]
    assert workflow["preset"] == "audit-log-integrity-contract-parallel-retention"
    assert [step["id"] for step in workflow["steps"]] == [
        "audit_contract_inspection_step",
        "audit_trail_builder_step",
        "audit_integrity_inspection_step",
        "retention_export_inspection_step",
        "audit_compliance_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["audit_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "audit_log_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "audit_log_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "audit_contract_inspection_step",
        "audit_trail_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "audit_contract_inspection_step",
        "audit_trail_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "audit_contract_inspection_step",
        "audit_trail_builder_step",
        "audit_integrity_inspection_step",
        "retention_export_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "audit-integrity",
        "audit-log",
        "permission-auth",
        "tenant-isolation",
        "privacy-redaction",
        "idempotency",
        "monitoring",
        "data-export",
        "retention-policy",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "deletion-retention" not in gatekeeper_verifies
    assert "backup-restore" not in gatekeeper_verifies
    assert "cache-invalidation" not in gatekeeper_verifies
    assert "dispute-chargeback" not in gatekeeper_verifies
    assert "message-delivery" not in gatekeeper_verifies
    assert "Audit Log Integrity Retention Workflow Notes" in bundle_text
    assert "data-lifecycle-contract-parallel-deletion-retention" not in bundle_text
    assert "Data Lifecycle Contract Inspector" not in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Confirm; use this audit" not in bundle_text


def test_success_categories_detect_audit_integrity_without_plain_audit_false_positive() -> None:
    labels = [label for label, _pattern in agent_candidate_success_surface_categories(AUDIT_TRAIL_TASK_TEXT)]
    plain_audit_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means audit log records key id, actor, scope, tenant, and failure reason."
        )
    ]
    weak_ui_history_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "成功必须让 UI history 显示一条管理员操作，并在数据库表里写一行记录。"
        )
    ]

    assert "audit/log-integrity-retention" in labels
    assert "audit/log" in labels
    assert "permission/auth" in labels
    assert "access/tenant-isolation" in labels
    assert "privacy/secrets-redaction" in labels
    assert "idempotency/duplicate-prevention" in labels
    assert "regression/monitoring-guard" in labels
    assert "data/export/report" in labels
    assert "audit/log" in plain_audit_labels
    assert "audit/log-integrity-retention" not in plain_audit_labels
    assert "audit/log-integrity-retention" not in weak_ui_history_labels


def test_fake_done_and_evidence_categories_detect_audit_integrity_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(AUDIT_TRAIL_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(AUDIT_TRAIL_TASK_TEXT)
    ]

    assert "audit/log-integrity-retention" in fake_labels
    assert "audit/log-integrity-retention" in evidence_labels
    assert "privacy/secrets-redaction" in evidence_labels
    assert "permission/auth" in evidence_labels
    assert "access/tenant-isolation" in evidence_labels
    assert "regression/monitoring-guard" in evidence_labels


def test_alignment_agreement_requires_audit_integrity_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Write one audit row and show it in the admin UI history.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means compliance audit trail proof covers create/update/delete, permission change, "
                    "failed attempt, append-only audit log, actor/subject/tenant/request id/IP/user agent/"
                    "before-after diff/reason code fields, PII/token redaction, monotonic timestamp and clock skew, "
                    "tamper-evident hash chain or WORM storage, retention policy, legal hold, SIEM/export "
                    "reconciliation, tenant isolation, retry no-miss/no-duplicate, and sequence gap alerts."
                ),
                "fake_done_risks": (
                    "An audit trail that is only a database row, console log, or UI history row without append-only "
                    "integrity, tamper evidence, retention/legal hold, SIEM/export reconciliation, tenant isolation, "
                    "privacy redaction, retry idempotency, and logging failure alerts must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include audit trail operation and failed-attempt fixtures, append-only or hash-chain "
                    "tamper negative checks, WORM/retention/legal-hold proof, SIEM/export reconciliation, tenant access "
                    "negative samples, PII/token redaction, retry no-miss/no-duplicate proof, and sequence gap alerts."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "audit/log-integrity-retention" in issue for issue in issues)
    assert any("fake-done risks" in issue and "audit/log-integrity-retention" in issue for issue in issues)
    assert any("evidence preferences" in issue and "audit/log-integrity-retention" in issue for issue in issues)


def test_agent_first_traceability_blocks_audit_row_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Write one audit row, print a console log, and show the row in UI history.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 本轮只要求数据库表记录、console log 和 UI history 可见。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: integrity protection, retention, export reconciliation, tenant boundaries, "
        "privacy redaction, retry correctness, and failure alerts can be handled later.\n"
        "  Owner: compliance platform owner\n"
        "  Follow-up: add audit hardening later.\n"
        "  Acceptance path: GateKeeper can pass after one audit row, console log, and UI history row exist.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 audit_logs 表里写一行记录、console log 输出和 UI history 展示，不处理完整性保护、"
        "留存、导出对账、租户边界、隐私脱敏、重试正确性或失败告警。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat integrity protection, retention, export reconciliation, tenant boundaries, privacy redaction, retry "
        "correctness, and failure alerts as later residual risk; only check one audit row, console log, and UI history row."
    )

    issues = alignment_agent_candidate_traceability_issues(AUDIT_TRAIL_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "audit/log-integrity-retention" in issue for issue in issues)
    assert any("fake-done risks" in issue and "audit/log-integrity-retention" in issue for issue in issues)
    assert any("evidence preferences" in issue and "audit/log-integrity-retention" in issue for issue in issues)
