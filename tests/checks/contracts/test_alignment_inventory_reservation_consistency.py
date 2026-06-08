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


INVENTORY_RESERVATION_TASK_TEXT = (
    "我要给 checkout 加库存预留和下单防超卖。成功必须证明同一个 SKU 在并发 checkout / payment webhook / "
    "cancellation / refund 下不会 oversell，reservation hold 有 TTL 到期释放，支付成功会确认并扣减库存，"
    "取消或失败支付会释放 hold，重复 webhook 和重试幂等，库存 ledger / order / payment provider 可对账，"
    "低库存和售罄状态对用户一致，race condition 有并发测试和监控告警，audit log 记录 reservation id、"
    "hold expiry、release reason 和 retry；只有单个用户 happy path 能下单或 UI 显示库存减少必须阻断。"
)


def test_cli_agent_plan_inventory_reservation_rounds_use_parallel_consistency_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-inventory-reservation-consistency",
    }
    task_message = (
        "Plan a governed Loop for checkout inventory reservation and oversell prevention. Success must prove same-SKU "
        "concurrent checkout and payment webhook paths cannot oversell; reservation holds have TTL expiry release; payment "
        "success confirms and decrements inventory; cancellation, refund, and failed payment release holds; duplicate webhook "
        "delivery and retries are idempotent; inventory ledger, order rows, and payment provider can reconcile; low-stock and "
        "sold-out states are consistent for users; race-condition recurrence has concurrency tests and monitoring alerts; audit "
        "records reservation id, hold expiry, release reason, retry id, actor, and order/payment links. Fake done is one-user "
        "happy path checkout, UI stock decrement, a DB decrement only, no TTL expiry proof, no webhook replay proof, no ledger "
        "reconciliation, or treating oversell risk as follow-up."
    )

    first_summary = _invoke_inventory_reservation_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_inventory_reservation_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Inventory Contract Inspector freezing SKU stock invariants, reservation state "
            "machine, hold TTL/expiry rules, payment webhook ordering, cancellation/refund/failed-payment release semantics, "
            "idempotency keys, ledger/order/provider reconciliation targets, sold-out/low-stock user-state expectations, audit "
            "fields, monitoring, and local governance. Inventory Reservation Builder implements only after that handoff. Then "
            "run Reservation Race Inspector and Payment Ledger Inspector in parallel: Reservation Race checks concurrent "
            "checkout, same-SKU oversell negatives, TTL expiry release, sold-out/low-stock consistency, and race monitoring; "
            "Payment Ledger checks webhook replay/order, payment success confirm/decrement, cancellation/refund/failed-payment "
            "release, idempotency, ledger/order/provider reconciliation, audit, and governance. GateKeeper must fail closed on "
            "one-user happy path, UI stock decrement only, DB decrement only, missing TTL expiry, missing webhook replay, "
            "missing release proof, missing reconciliation, missing sold-out consistency, missing audit/monitoring, or skipped "
            "local governance."
        ),
        env=env,
    )
    _assert_inventory_reservation_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_inventory_reservation_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this inventory reservation contract-first parallel evidence direction.",
        env=env,
    )
    _assert_inventory_reservation_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _inventory_reservation_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_inventory_reservation_bundle(bundle_text)


def _invoke_inventory_reservation_plan_round(
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


def _assert_inventory_reservation_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Inventory Contract Inspector" in agreement_text
    assert "Inventory Reservation Builder" in agreement_text
    assert "Reservation Race Inspector" in agreement_text
    assert "Payment Ledger Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "payment provider webhook and ledger task" not in agreement_text
    assert "Builder -> Inspector -> Guide" not in agreement_text


def _assert_inventory_reservation_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("inventory reservation", "oversell", "TTL", "webhook", "ledger", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this inventory" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _inventory_reservation_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_inventory_reservation_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "inventory-contract-inspector",
        "inventory-reservation-builder",
        "reservation-race-inspector",
        "payment-ledger-inspector",
        "inventory-reservation-gatekeeper",
    ]
    assert workflow["preset"] == "inventory-reservation-contract-parallel-consistency"
    assert [step["id"] for step in workflow["steps"]] == [
        "inventory_contract_inspection_step",
        "inventory_reservation_builder_step",
        "reservation_race_inspection_step",
        "payment_ledger_inspection_step",
        "inventory_reservation_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["inventory_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "inventory_reservation_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "inventory_reservation_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "inventory_contract_inspection_step",
        "inventory_reservation_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "inventory_contract_inspection_step",
        "inventory_reservation_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "inventory_contract_inspection_step",
        "inventory_reservation_builder_step",
        "reservation_race_inspection_step",
        "payment_ledger_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "inventory-reservation",
        "conflict-resolution",
        "webhook-ordering",
        "idempotency",
        "ledger-reconciliation",
        "payment-refund-billing",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "Inventory Reservation Workflow Notes" in bundle_text
    assert "payment-webhook-contract-parallel-controls" not in bundle_text
    assert "payment provider webhook and ledger task" not in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "Builder -> Inspector -> Guide" not in bundle_text
    assert "Confirm; use this inventory" not in bundle_text


def test_success_categories_detect_inventory_reservation_without_stock_report_false_positive() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means inventory reservation consistency proves SKU checkout cannot oversell under concurrent "
            "payment webhooks, hold TTL expiry releases stock, cancellation and refund release holds, retries are "
            "idempotent, inventory ledger reconciliation passes, sold-out status is consistent, and monitoring "
            "alerts cover race-condition recurrence."
        )
    ]
    report_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means admins can export a stock report with current SKU counts and CSV totals."
        )
    ]

    assert "inventory/reservation-consistency" in labels
    assert "idempotency/duplicate-prevention" in labels
    assert "audit/log" in labels
    assert "regression/monitoring-guard" in labels
    assert "inventory/reservation-consistency" not in report_labels


def test_success_categories_do_not_treat_contract_inventory_as_stock_reservation() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means a deletion contract inventory proves retention exceptions, backup expiry handling, "
            "search purge, audit-log retention, and tenant isolation for GDPR erase requests."
        )
    ]

    assert "inventory/reservation-consistency" not in labels
    assert "data-lifecycle/deletion-retention" in labels


def test_fake_done_and_evidence_categories_detect_single_checkout_reservation_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(INVENTORY_RESERVATION_TASK_TEXT)]
    evidence_labels = [
        label for label, _pattern in agent_candidate_evidence_preference_categories(INVENTORY_RESERVATION_TASK_TEXT)
    ]

    assert "inventory/reservation-consistency" in fake_labels
    assert "inventory/reservation-consistency" in evidence_labels
    assert "happy-path-only" in fake_labels
    assert "idempotency/duplicate-prevention" in evidence_labels


def test_alignment_agreement_requires_inventory_reservation_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a checkout path where a single user can place one order and the UI shows stock decreasing.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means inventory reservation consistency proves concurrent checkout and payment webhook "
                    "paths cannot oversell the same SKU, hold TTL expiry releases stock, cancellation/refund/failed "
                    "payment release holds, duplicate webhook retry is idempotent, inventory ledger/order/provider "
                    "reconciliation passes, sold-out and low-stock states are consistent, and audit records "
                    "reservation id, hold expiry, release reason, and retry."
                ),
                "fake_done_risks": (
                    "A single-user happy path or UI stock decrement without oversell prevention, hold expiry release, "
                    "cancellation/refund release, idempotent webhook retry, ledger reconciliation, sold-out state, "
                    "monitoring, and audit proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include concurrent checkout race tests, payment webhook replay/idempotency, "
                    "hold TTL expiry release, cancellation/refund release, inventory ledger reconciliation, "
                    "sold-out/low-stock checks, monitoring alerts, and audit log proof."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "inventory/reservation-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "inventory/reservation-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "inventory/reservation-consistency" in issue for issue in issues)


def test_agent_first_traceability_blocks_single_checkout_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a checkout path where a single user can place one order and the UI shows stock decreasing.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 暂不把 oversell prevention、hold TTL expiry release、cancellation/refund release 或 inventory ledger "
        "reconciliation 作为本轮阻断项。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: concurrent checkout oversell prevention, payment webhook replay idempotency, "
        "hold TTL expiry release, cancellation/refund release, inventory ledger reconciliation, sold-out state, "
        "monitoring, audit, and retry proof can be handled later.\n"
        "  Owner: checkout owner\n"
        "  Follow-up: add inventory reservation hardening later.\n"
        "  Acceptance path: GateKeeper can pass after a single checkout happy path and UI stock decrement.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现单个用户 happy path 下单和 UI 库存减少，不处理 concurrent checkout oversell prevention、"
        "payment webhook replay idempotency、hold TTL expiry release、cancellation/refund release、"
        "inventory ledger reconciliation、sold-out state、monitoring、audit 或 retry proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat oversell prevention, hold expiry release, cancellation/refund release, webhook idempotency, "
        "inventory ledger reconciliation, sold-out state, monitoring, audit, and retry proof as later residual risk; "
        "only check a single checkout happy path and UI stock decrement.\n"
    )

    issues = alignment_agent_candidate_traceability_issues(INVENTORY_RESERVATION_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "inventory/reservation-consistency" in issue for issue in issues)
    assert any("fake-done risks" in issue and "inventory/reservation-consistency" in issue for issue in issues)
    assert any("evidence preferences" in issue and "inventory/reservation-consistency" in issue for issue in issues)
    assert any("success criteria" in issue and "idempotency/duplicate-prevention" in issue for issue in issues)
