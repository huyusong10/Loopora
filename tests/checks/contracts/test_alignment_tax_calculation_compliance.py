from __future__ import annotations

import json
from pathlib import Path

from agent_bundle_candidates_test_support import CliRunner, _invoke_codex_plan, yaml
from alignment_test_support import _wait_for_status
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


TAX_CALCULATION_TASK_TEXT = (
    "我要给 checkout 加 sales tax / VAT / GST 计算。成功必须证明 US state nexus、EU VAT、GST、"
    "shipping address / billing address、digital goods 和 physical goods taxability、tax exemption certificate、"
    "B2B reverse charge、discount、coupon、shipping fee、refund、currency rounding 都计算正确，"
    "tax provider sandbox 和本地 tax ledger / invoice 可对账，tax inclusive / exclusive 价格展示一致，"
    "rate change 生效日期和 timezone 正确，audit log 记录 tax calculation version、jurisdiction、rate source、"
    "exemption id 和 provider request id；只有 checkout 显示一个 tax 数字或 provider 返回一个 rate 必须阻断。"
)


def test_cli_agent_plan_tax_calculation_rounds_use_parallel_compliance_workflow(sample_workdir: Path) -> None:
    runner = CliRunner()
    env = {
        "LOOPORA_FAKE_EXECUTOR": "success",
        "LOOPORA_AGENT_SESSION_ID": "codex-plan-tax-calculation-compliance",
    }
    task_message = (
        "Plan a governed Loop for checkout tax calculation compliance. Success must prove taxable nexus, US state "
        "sales tax, EU VAT, GST, shipping-address and billing-address jurisdiction selection, product tax category "
        "for digital and physical goods, customer exemption certificates, B2B reverse charge, inclusive and exclusive "
        "tax display, discount/coupon/shipping/refund tax rounding, invoice and receipt line item totals, refund and "
        "credit memo tax reversal, tax provider sandbox fallback/retry/idempotency, rate effective date and timezone, "
        "audit trail with jurisdiction, rate, rate version, exemption id, provider request id, and reconciliation to "
        "provider reports. Fake done is one checkout tax number, a hardcoded rate, provider quote only, UI total only, "
        "no refund or exemption proof, no jurisdiction matrix, no rounding negatives, or treating tax ledger "
        "reconciliation as follow-up."
    )

    first_summary = _invoke_tax_plan_round(runner, sample_workdir, message=task_message, env=env)
    assert first_summary["ready"] is False
    assert first_summary["loop_recovery"] == "finish_web_review"

    second_summary = _invoke_tax_plan_round(
        runner,
        sample_workdir,
        message=(
            "Additional judgment: start with Tax Contract Inspector freezing jurisdiction matrix, nexus, product "
            "taxability, exemption/reverse-charge, inclusive/exclusive display, discount/coupon/shipping/refund "
            "rounding, invoice/receipt line item totals, refund/credit memo reversal, provider sandbox fallback/"
            "retry/idempotency, effective-date timezone, audit fields, provider-report reconciliation, migration/"
            "backward compatibility, and local governance. Tax Calculation Builder implements only after that handoff. "
            "Then run Jurisdiction Rate Inspector and Invoice Reversal Inspector in parallel: Jurisdiction Rate checks "
            "nexus, US/EU/GST jurisdiction/address matrix, taxability, exemption/reverse-charge, provider fallback/"
            "idempotency, effective-date timezone; Invoice Reversal checks rounding, inclusive/exclusive totals, "
            "invoice/receipt totals, refund/credit memo reversal, provider-report reconciliation, audit fields, "
            "monitoring, compatibility, and governance. GateKeeper must fail closed on one tax number, hardcoded rate, "
            "provider quote only, UI total only, missing jurisdiction matrix, missing exemption/reverse-charge, "
            "missing refund/reversal, missing rounding proof, missing reconciliation, missing audit/monitoring, or "
            "skipped local governance."
        ),
        env=env,
    )
    _assert_tax_agreement_round(second_summary, first_summary["alignment_session_id"])

    third_summary = _invoke_tax_plan_round(
        runner,
        sample_workdir,
        message="Confirm; use this tax calculation contract-first parallel compliance direction.",
        env=env,
    )
    _assert_tax_ready_round(third_summary, first_summary["alignment_session_id"])
    bundle_text = _tax_bundle_text(sample_workdir, third_summary["alignment_session_id"])
    _assert_tax_bundle(bundle_text)


def _invoke_tax_plan_round(
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


def _assert_tax_agreement_round(second_summary: dict, alignment_session_id: str) -> None:
    assert second_summary["ready"] is False
    assert second_summary["loop_recovery"] == "continue_alignment_dialogue"
    assert second_summary["continued_alignment_session"] is True
    assert second_summary["alignment_session_id"] == alignment_session_id
    assert second_summary["status"] == "waiting_user"
    assert second_summary["question_action"]["must_wait_for_user_reply"] is True
    assert second_summary["alignment_stage"] == "agreement_ready"
    agreement_text = second_summary["alignment_assistant_message"]
    assert "Tax Contract Inspector" in agreement_text
    assert "Tax Calculation Builder" in agreement_text
    assert "Jurisdiction Rate Inspector" in agreement_text
    assert "Invoice Reversal Inspector" in agreement_text
    assert "parallel" in agreement_text
    assert "task-evidence-repair" not in agreement_text
    assert "payment provider webhook and ledger task" not in agreement_text
    assert "Webhook Contract Inspector" not in agreement_text


def _assert_tax_ready_round(third_summary: dict, alignment_session_id: str) -> None:
    assert third_summary["ready"] is True
    assert third_summary["continued_alignment_session"] is True
    assert third_summary["alignment_session_id"] == alignment_session_id
    ready_projection_text = json.dumps(third_summary["ready_review_projection"], ensure_ascii=False)
    for term in ("tax", "jurisdiction", "exemption", "rounding", "refund", "reconciliation", "audit"):
        assert term in ready_projection_text
    assert "Confirm; use this tax" not in ready_projection_text
    assert third_summary["ready_review_projection"]["traceability"]["mapped_count"] == third_summary[
        "ready_review_projection"
    ]["traceability"]["required_count"]


def _tax_bundle_text(sample_workdir: Path, alignment_session_id: str) -> str:
    return (
        sample_workdir
        / ".loopora"
        / "alignment_sessions"
        / alignment_session_id
        / "artifacts"
        / "bundle.yml"
    ).read_text(encoding="utf-8")


def _assert_tax_bundle(bundle_text: str) -> None:
    bundle = yaml.safe_load(bundle_text)
    workflow = bundle["workflow"]
    assert [role["key"] for role in bundle["role_definitions"]] == [
        "tax-contract-inspector",
        "tax-calculation-builder",
        "jurisdiction-rate-inspector",
        "invoice-reversal-inspector",
        "tax-compliance-gatekeeper",
    ]
    assert workflow["preset"] == "tax-calculation-contract-parallel-compliance"
    assert [step["id"] for step in workflow["steps"]] == [
        "tax_contract_inspection_step",
        "tax_calculation_builder_step",
        "jurisdiction_rate_inspection_step",
        "invoice_reversal_inspection_step",
        "tax_compliance_gatekeeper_step",
    ]
    assert workflow["steps"][1]["inputs"]["handoffs_from"] == ["tax_contract_inspection_step"]
    assert workflow["steps"][2]["parallel_group"] == "tax_calculation_review_pack"
    assert workflow["steps"][3]["parallel_group"] == "tax_calculation_review_pack"
    assert workflow["steps"][2]["inputs"]["handoffs_from"] == [
        "tax_contract_inspection_step",
        "tax_calculation_builder_step",
    ]
    assert workflow["steps"][3]["inputs"]["handoffs_from"] == [
        "tax_contract_inspection_step",
        "tax_calculation_builder_step",
    ]
    assert workflow["steps"][-1]["inputs"]["handoffs_from"] == [
        "tax_contract_inspection_step",
        "tax_calculation_builder_step",
        "jurisdiction_rate_inspection_step",
        "invoice_reversal_inspection_step",
    ]
    gatekeeper_verifies = workflow["steps"][-1]["inputs"]["evidence_query"]["verifies"]
    for verify_ref in (
        "tax-compliance",
        "provider-contract",
        "idempotency",
        "retry-timeout",
        "ledger-reconciliation",
        "payment-refund-billing",
        "audit-log",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ):
        assert verify_ref in gatekeeper_verifies
    assert "message-delivery" not in gatekeeper_verifies
    assert "Tax Calculation Compliance Workflow Notes" in bundle_text
    assert "task-evidence-repair" not in bundle_text
    assert "payment-webhook-contract-parallel-controls" not in bundle_text
    assert "Webhook Contract Inspector" not in bundle_text
    assert "Confirm; use this tax" not in bundle_text


def test_success_categories_detect_tax_calculation_without_tax_report_false_positive() -> None:
    labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means tax calculation compliance proves US state nexus, EU VAT, GST, shipping and billing "
            "address jurisdiction, digital and physical goods taxability, exemption certificates, B2B reverse charge, "
            "discounts, coupons, shipping fee, refund, currency rounding, tax provider sandbox, tax ledger invoice "
            "reconciliation, inclusive/exclusive display, rate effective date, timezone, and audit version."
        )
    ]
    report_labels = [
        label
        for label, _pattern in agent_candidate_success_surface_categories(
            "Success means admins can export a tax report CSV with monthly totals."
        )
    ]

    assert "tax/calculation-compliance" in labels
    assert "payment/refund/billing" in labels
    assert "external/provider-contract" in labels
    assert "audit/log" in labels
    assert "tax/calculation-compliance" not in report_labels


def test_fake_done_and_evidence_categories_detect_checkout_tax_number_only_risk() -> None:
    fake_labels = [label for label, _pattern in agent_candidate_fake_done_categories(TAX_CALCULATION_TASK_TEXT)]
    evidence_labels = [label for label, _pattern in agent_candidate_evidence_preference_categories(TAX_CALCULATION_TASK_TEXT)]

    assert "tax/calculation-compliance" in fake_labels
    assert "tax/calculation-compliance" in evidence_labels
    assert "payment/refund/billing" in fake_labels
    assert "external/provider-contract" in evidence_labels


def test_alignment_agreement_requires_tax_calculation_compliance_evidence(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a checkout tax number display and one provider sandbox rate lookup.",
    )
    session = {
        "working_agreement": {
            "readiness_evidence": {
                "success_surface": (
                    "Success means tax calculation compliance proves US state nexus, EU VAT/GST, shipping/billing "
                    "address jurisdiction, digital/physical goods taxability, exemption certificate, reverse charge, "
                    "discount/coupon/shipping fee/refund/currency rounding, tax provider sandbox and local tax "
                    "ledger/invoice reconciliation, inclusive/exclusive display, rate effective date/timezone, and audit "
                    "tax calculation version, jurisdiction, rate source, exemption id, and provider request id."
                ),
                "fake_done_risks": (
                    "A checkout tax number or one provider rate without jurisdiction, taxability, exemption, reverse "
                    "charge, rounding, refund, provider/ledger reconciliation, inclusive/exclusive display, rate "
                    "effective date, timezone, and audit proof must be blocked."
                ),
                "evidence_preferences": (
                    "Evidence must include jurisdiction matrix cases, taxability cases, exemption/reverse-charge cases, "
                    "discount/coupon/shipping/refund rounding cases, provider sandbox responses, tax ledger invoice "
                    "reconciliation, inclusive/exclusive display checks, rate effective date/timezone checks, and audit log proof."
                ),
            }
        }
    }

    issues = alignment_bundle_agreement_traceability_issues(session, bundle)

    assert any("success surface" in issue and "tax/calculation-compliance" in issue for issue in issues)
    assert any("fake-done risks" in issue and "tax/calculation-compliance" in issue for issue in issues)
    assert any("evidence preferences" in issue and "tax/calculation-compliance" in issue for issue in issues)


def test_agent_first_traceability_blocks_checkout_tax_number_only_candidate(sample_workdir: Path) -> None:
    bundle = load_bundle_text(alignment_bundle_yaml(str(sample_workdir)))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience for the target user in the target workdir with small, maintainable changes that preserve the primary user-facing flow.",
        "Ship a checkout tax number display and one provider sandbox rate lookup.",
    )
    bundle["spec"]["markdown"] += (
        "\n# Fake Done\n"
        "- 暂不把 jurisdiction matrix、taxability、exemption certificate、reverse charge、rounding 或 tax ledger "
        "reconciliation 作为本轮阻断项。\n"
        "\n# Residual Risk\n"
        "- Accepted residual risk: jurisdiction matrix, taxability, exemption certificate, reverse charge, "
        "discount/coupon/shipping/refund/currency rounding, provider/ledger reconciliation, inclusive/exclusive "
        "display, rate effective date/timezone, audit, and provider request proof can be handled later.\n"
        "  Owner: tax owner\n"
        "  Follow-up: add tax compliance hardening later.\n"
        "  Acceptance path: GateKeeper can pass after checkout displays one tax number and provider returns one rate.\n"
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n只实现 checkout 显示一个 tax 数字和 provider 返回一个 rate，不处理 jurisdiction matrix、taxability、"
        "exemption certificate、reverse charge、discount/coupon/shipping/refund/currency rounding、tax ledger reconciliation、"
        "inclusive/exclusive display、rate effective date/timezone、audit 或 provider request proof。\n"
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\nTreat jurisdiction matrix, taxability, exemption certificate, reverse charge, rounding, refund, "
        "tax ledger reconciliation, inclusive/exclusive display, rate effective date/timezone, audit, and provider request "
        "proof as later residual risk; only check checkout displays one tax number and provider returns one rate."
    )

    issues = alignment_agent_candidate_traceability_issues(TAX_CALCULATION_TASK_TEXT, bundle)

    assert any("success criteria" in issue and "tax/calculation-compliance" in issue for issue in issues)
    assert any("fake-done risks" in issue and "tax/calculation-compliance" in issue for issue in issues)
    assert any("evidence preferences" in issue and "tax/calculation-compliance" in issue for issue in issues)


def test_default_task_anchored_plan_projects_tax_calculation_domain_keys(
    service_factory,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "generic-tax-workdir"
    workdir.mkdir()
    service = service_factory(scenario="success")

    created = service.create_alignment_session(
        workdir=workdir,
        message=(
            TAX_CALCULATION_TASK_TEXT
            + " 请优先证明 jurisdiction matrix、taxability、provider sandbox、tax ledger / invoice reconciliation、"
            "inclusive / exclusive display、rate effective date / timezone 和 audit version。"
        ),
    )
    agreement = _wait_for_status(service, created["id"], "waiting_user")

    assert agreement["alignment_stage"] == "agreement_ready"
    service.append_alignment_message(created["id"], "确认，采用这个方向。")
    ready = _wait_for_status(service, created["id"], "ready")
    bundle = load_bundle_text(Path(ready["bundle_path"]).read_text(encoding="utf-8"))
    spec_markdown = bundle["spec"]["markdown"]
    success_surface = spec_markdown.split("# Success Surface", 1)[1].split("# Fake Done", 1)[0]
    fake_done = spec_markdown.split("# Fake Done", 1)[1].split("# Evidence Preferences", 1)[0]
    evidence_preferences = spec_markdown.split("# Evidence Preferences", 1)[1].split("# Execution Strategy", 1)[0]
    inspect_verifies = bundle["workflow"]["steps"][1]["inputs"]["evidence_query"]["verifies"]
    gatekeeper_verifies = bundle["workflow"]["steps"][-1]["inputs"]["evidence_query"]["verifies"]

    assert "税务 jurisdiction matrix" in success_surface
    assert "taxability" in success_surface
    assert "provider sandbox" in success_surface
    assert "ledger/invoice 对账" in success_surface
    assert "effective-date/timezone" in success_surface
    assert "audit-version 证明" in success_surface
    assert "tax-number/provider-rate-only 负向样本" in fake_done
    assert "税务 jurisdiction matrix" in evidence_preferences
    assert "provider sandbox" in evidence_preferences
    assert "ledger/invoice 对账" in evidence_preferences
    assert "tax-compliance" in inspect_verifies
    assert "provider-contract" in inspect_verifies
    assert "payment-refund-billing" in gatekeeper_verifies
    assert "audit-log" in gatekeeper_verifies
    assert "audit-integrity" not in gatekeeper_verifies
