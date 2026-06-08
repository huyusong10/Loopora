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


USAGE_QUOTA_TASK_TEXT = (
    "我要给 SaaS API 加 usage metering 和 plan quota enforcement。成功必须证明同一个 org 在并发 API calls、"
    "duplicate usage events、retry、plan upgrade/downgrade、billing period reset、grace limit 和 hard limit 下不会超用或少计，"
    "quota window / reset timezone 正确，usage ledger / invoice / subscription provider 可对账，幂等 key 防止重复扣量，"
    "超限请求返回一致错误且不会绕过权限，低余量和超限告警准确，audit log 记录 usage event id、metering version、"
    "quota window、reset run 和 retry；只有 dashboard 显示用量或单次 API 调用被 429 阻断必须阻断。"
)


def test_cli_agent_plan_usage_quota_rounds_use_parallel_metering_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-usage-quota-metering",
    }
    task_message = (
        "Plan a governed Loop for SaaS API usage metering and plan quota enforcement. Success must prove the same org "
        "cannot overuse or be undercounted under concurrent API calls, duplicate usage events, retries, plan upgrade/"
        "downgrade, billing period reset, grace limit, and hard limit; quota window and reset timezone are correct; "
        "usage ledger, invoice, and subscription provider reconcile; idempotency keys prevent double charging or double "
        "decrement; over-limit requests return permission-safe consistent errors; low-quota and exhausted-quota alerts "
        "are accurate; audit log records usage event id, metering version, quota window, reset run, retry id, actor, org, "
        "and plan. Fake done is a dashboard showing usage, one API call returning 429, a cron reset only, provider total "
        "only, ignoring duplicate events, no concurrent proof, no plan-change proof, or treating ledger reconciliation as follow-up."
    )

    first_summary = _invoke_usage_quota_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_usage_quota_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Quota Contract Inspector freezing usage event schema, idempotency keys, "
            "org/plan/quota window invariants, concurrent call accounting, duplicate event handling, retry semantics, "
            "plan upgrade/downgrade behavior, billing reset timezone, grace/hard limit behavior, permission-safe over-limit "
            "errors, ledger/invoice/subscription-provider reconciliation, audit fields, monitoring alerts, and local governance. "
            "Usage Metering Builder implements only after that handoff. Then run Quota Race Inspector and Billing Reconciliation "
            "Inspector in parallel: Quota Race checks concurrent calls, duplicate usage events, retry idempotency, hard/grace "
            "limits, reset timezone, and permission-safe errors; Billing Reconciliation checks plan changes, ledger/invoice/"
            "provider reconciliation, low/exhausted alerts, audit metering version/window/reset/retry fields, migration/"
            "compatibility, and governance. GateKeeper must fail closed on dashboard-only usage, single 429, cron reset only, "
            "provider total only, missing duplicate-event proof, missing concurrency proof, missing plan-change proof, missing "
            "reset timezone proof, missing reconciliation, missing audit/monitoring, or skipped local governance."
        ),
        env=env,
    )
    _assert_usage_quota_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_usage_quota_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this usage/quota contract-first parallel metering direction.",
        env=env,
    )
    _assert_usage_quota_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _usage_quota_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_usage_quota_bundle(bundle_text)


def _invoke_usage_quota_plan_round(
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


def _assert_usage_quota_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Quota Contract Inspector" in agreement_text
    assert "Usage Metering Builder" in agreement_text
    assert "Quota Race Inspector" in agreement_text
    assert "Billing Reconciliation Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "payment provider webhook and ledger task" not in agreement_text
    assert "checkout.session.completed" not in agreement_text
    assert "Webhook Contract Inspector" not in agreement_text


def _assert_usage_quota_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("usage", "quota", "duplicate", "reset", "reconciliation", "audit", "monitoring"):
        assert term in ready_projection_text
    assert "Confirm; use this usage" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _usage_quota_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_usage_quota_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "quota-contract-inspector",
        "usage-metering-builder",
        "quota-race-inspector",
        "billing-reconciliation-inspector",
        "usage-quota-gatekeeper",
    ]
    assert workflow["preset"] == "usage-quota-contract-parallel-metering"
    assert [step["id"] for step in workflow["steps"]] == [
        "quota_contract_inspection_step",
        "usage_metering_builder_step",
        "quota_race_inspection_step",
        "billing_reconciliation_inspection_step",
        "usage_quota_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["quota_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "usage_quota_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "usage_quota_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "quota_contract_inspection_step",
        "usage_metering_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "quota_contract_inspection_step",
        "usage_metering_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "quota_contract_inspection_step",
        "usage_metering_builder_step",
        "quota_race_inspection_step",
        "billing_reconciliation_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "quota-metering",
        "idempotency",
        "conflict-resolution",
        "permission-auth",
        "ledger-reconciliation",
        "payment-refund-billing",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Usage Quota Metering Workflow Notes" in bundle_text
    assert "payment-webhook-contract-parallel-controls" not in bundle_text
    assert "Webhook Contract Inspector" not in bundle_text
    assert "checkout.session.completed" not in bundle_text
    assert "Confirm; use this usage" not in bundle_text


def test_success_categories_detect_usage_quota_without_inventory_false_positive() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means usage metering and quota enforcement prove concurrent API calls, duplicate usage events, "
            "plan upgrade/downgrade, billing period reset, hard limits, grace limits, quota windows, reset timezone, "
            "usage ledger reconciliation, idempotent keys, low-balance alerts, and audit metering version."
        )
    ]
    inventory_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means inventory reservation consistency proves SKU checkout cannot oversell and reservation "
            "hold TTL expiry releases stock."
        )
    ]
    report_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means admins can export a stock report with current SKU counts and CSV totals."
        )
    ]

    assert "usage/quota-metering" in labels
    assert "idempotency/duplicate-prevention" in labels
    assert "audit/log" in labels
    assert "regression/monitoring-guard" in labels
    assert "inventory/reservation-consistency" not in labels
    assert "usage/quota-metering" not in inventory_labels
    assert "inventory/reservation-consistency" not in report_labels


def test_fake_done_and_evidence_categories_detect_dashboard_or_single_429_usage_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(USAGE_QUOTA_TASK_TEXT)]
    evidence_labels = [label for label, _pattern in agent_candidate_evidence_preference_categories(USAGE_QUOTA_TASK_TEXT)]

    assert "usage/quota-metering" in fake_labels
    assert "usage/quota-metering" in evidence_labels
    assert "data/export/report" in fake_labels
    assert "idempotency/duplicate-prevention" in evidence_labels
    assert "inventory/reservation-consistency" not in fake_labels
    assert "inventory/reservation-consistency" not in evidence_labels


def test_alignment_agreement_requires_usage_quota_metering_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a usage dashboard and block one over-limit API call with 429.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means usage quota metering proves concurrent API calls, duplicate usage events, retries, "
                    "plan upgrade/downgrade, billing period reset, grace limit, hard limit, quota window timezone, "
                    "usage ledger/invoice/subscription provider reconciliation, idempotent keys, permission-safe "
                    "over-limit errors, low-balance alerts, and audit metering version."
                ),
                "fake_done_risks": (
                    "A dashboard showing usage or one API call blocked with 429 without concurrent metering, duplicate "
                    "event idempotency, plan-change behavior, billing-period reset, quota window timezone, ledger "
                    "reconciliation, permission-safe errors, alerts, and audit proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include concurrent API usage metering, duplicate usage event idempotency, plan "
                    "upgrade/downgrade, reset timezone, hard/grace limit behavior, ledger/invoice/provider "
                    "reconciliation, permission-safe over-limit error, low-balance alerts, audit logs, and retry proof."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "usage/quota-metering" in issue for issue in issues)
    assert any("fake-done risks" in issue and "usage/quota-metering" in issue for issue in issues)
    assert any("evidence preferences" in issue and "usage/quota-metering" in issue for issue in issues)


def test_agent_first_traceability_blocks_usage_dashboard_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a usage dashboard and block one over-limit API call with 429.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 暂不把 duplicate usage events、plan upgrade/downgrade、billing period reset、quota window timezone "
        "或 usage ledger reconciliation 作为本轮阻断项。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: concurrent API usage metering, duplicate usage event idempotency, plan "
        "upgrade/downgrade, billing period reset, grace/hard limit behavior, quota window timezone, usage ledger "
        "reconciliation, permission-safe over-limit errors, low-balance alerts, audit, and retry proof can be handled later.\n"
        "  Owner: platform owner\n"
        "  Follow-up: add quota metering hardening later.\n"
        "  Acceptance path: GateKeeper can pass after dashboard usage display and one API call returns 429.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 dashboard 显示用量和单次 API 调用被 429 阻断，不处理 concurrent API usage metering、"
        "duplicate usage event idempotency、plan upgrade/downgrade、billing period reset、quota window timezone、"
        "usage ledger reconciliation、permission-safe over-limit errors、low-balance alerts、audit 或 retry proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat concurrent API usage metering, duplicate usage event idempotency, plan upgrade/downgrade, "
        "billing period reset, quota window timezone, usage ledger reconciliation, permission-safe over-limit errors, "
        "low-balance alerts, audit, and retry proof as later residual risk; only check dashboard usage display and one 429."
    )

    issues = alignment_agent_candidate_traceability_issues(USAGE_QUOTA_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "usage/quota-metering" in issue for issue in issues)
    assert any("fake-done risks" in issue and "usage/quota-metering" in issue for issue in issues)
    assert any("evidence preferences" in issue and "usage/quota-metering" in issue for issue in issues)
    assert any("success criteria" in issue and "idempotency/duplicate-prevention" in issue for issue in issues)
