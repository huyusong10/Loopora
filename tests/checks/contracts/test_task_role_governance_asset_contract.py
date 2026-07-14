from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from compacted_contract_support import assert_contains_all
from loopora import executor_alignment_agreement_evidence as agreement_evidence_module
from loopora import executor_alignment_payloads as alignment_payload_module
from loopora import executor_alignment_preconfirmation_payloads as preconfirmation_payload_module
from loopora import executor_alignment_readiness_payloads as readiness_payload_module
from loopora import executor_alignment_bundle_task_roles as task_role_module
from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intent_module
from loopora.alignment_guidance import load_alignment_guidance_assets
from loopora.alignment_readiness_shared import ALIGNMENT_READINESS_EVIDENCE_KEYS


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

    projection_source = "\n".join(
        (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename in (
            "executor_alignment_task_projection.py",
            "executor_alignment_task_projection_scope.py",
        )
    )
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


def test_specialized_workflow_display_names_live_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    display_names = assets.specialized_workflow_display_names
    assert set(display_names["rag-grounding-long-chain"]) == {"en", "zh", "es"}
    assert display_names["rag-grounding-long-chain"]["en"] == "RAG Grounding Long-Chain Loop"
    assert display_names["payment-webhook-contract-parallel-controls"]["zh"] == "支付 Webhook Ledger Loop"
    assert display_names["key-rotation-contract-parallel-controls"]["es"] == "Loop de key rotation lifecycle"

    specialized_shell_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_specialized_shell.py").read_text(encoding="utf-8")
    assert "specialized-workflow-display-names.json" in specialized_shell_source
    for snippet in (
        "RAG Grounding Long-Chain Loop",
        "支付 Webhook Ledger Loop",
        "Loop de key rotation lifecycle",
    ):
        assert snippet not in specialized_shell_source


def test_task_workflow_intent_copy_lives_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    workflow_intents = assets.task_workflow_intents
    assert set(workflow_intents["data_residency"]) == {"en", "zh", "es"}
    assert workflow_intents["data_residency"]["en"].startswith("Use a data residency contract-first workflow")
    assert "tenant-field-only" in workflow_intents["data_residency"]["en"]
    assert "happy-path-webhook-only" in workflow_intents["payment_webhook_ledger"]["en"]
    assert "long-chain RAG workflow" in workflow_intents["rag_long_chain"]["en"]

    intent_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_workflow_intents.py").read_text(encoding="utf-8")
    assert "task-workflow-intents.json" in intent_source
    for snippet in (
        "Use a data residency contract-first workflow",
        "tenant-field-only",
        "happy-path-webhook-only",
        "long-chain RAG workflow",
    ):
        assert snippet not in intent_source


def test_task_workflow_intent_asset_keys_have_compatibility_setters() -> None:
    assets = load_alignment_guidance_assets()
    replacers = dict(workflow_intent_module.TASK_WORKFLOW_INTENT_REPLACERS)
    assert set(replacers) == set(assets.task_workflow_intents)
    for function_name in replacers.values():
        assert callable(getattr(workflow_intent_module, function_name))


def test_task_spec_workflow_note_copy_lives_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    spec_notes = assets.task_spec_workflow_notes
    assert set(spec_notes["cdc_replication_consistency"]["locales"]) == {"en", "zh", "es"}
    assert spec_notes["cdc_replication_consistency"]["marker"] == "# CDC Replication Consistency Workflow Notes"
    assert "green-sync-job-only" in spec_notes["cdc_replication_consistency"]["locales"]["en"]
    assert "narrative-only root cause" in spec_notes["incident_root_cause"]["locales"]["en"]
    assert "chart-only" in spec_notes["metric_reporting_reconciliation"]["locales"]["en"]

    spec_notes_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_notes.py").read_text(encoding="utf-8")
    append_note_scaffold_sources = [
        (REPO_ROOT / "src" / "loopora" / filename).read_text(encoding="utf-8")
        for filename in (
            "executor_alignment_bundle_task_spec_scaffolds_commercial.py",
            "executor_alignment_bundle_task_spec_scaffolds_data.py",
            "executor_alignment_bundle_task_spec_scaffolds_operations.py",
            "executor_alignment_bundle_task_spec_scaffolds_product_engagement.py",
            "executor_alignment_bundle_task_spec_scaffolds_product_operations.py",
            "executor_alignment_bundle_task_spec_scaffolds_product_search_ai.py",
            "executor_alignment_bundle_task_spec_scaffolds_trust_access.py",
        )
    ]
    assert "task-spec-workflow-notes.json" in spec_notes_source
    assert "append_task_spec_workflow_note_for_task" in spec_notes_source
    assert "append_task_spec_workflow_note_from_asset" in spec_notes_source
    for scaffold_source in append_note_scaffold_sources:
        assert "append_task_spec_workflow_note_for_task" in scaffold_source
        assert "append_task_spec_workflow_note_from_asset" not in scaffold_source
    for snippet in (
        "green-sync-job-only",
        "narrative-only root cause",
        "chart-only",
    ):
        for scaffold_source in append_note_scaffold_sources:
            assert snippet not in scaffold_source


def test_task_spec_scaffold_templates_live_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    templates = assets.task_spec_scaffold_templates
    expected_templates = {
        "authorization_policy",
        "concurrency_conflict_resolution",
        "data_residency",
        "identity_sso",
        "key_rotation",
        "kyc_aml_screening",
        "payment_webhook_ledger",
        "prompt_asset_ownership",
        "schedule_phase",
        "search_index_consistency",
        "search_quality",
        "support_impersonation",
    }
    assert set(templates) >= expected_templates
    for template_key in expected_templates:
        assert set(templates[template_key]["locales"]) == {"en", "zh", "es"}
        for template in templates[template_key]["locales"].values():
            assert template.startswith("# Task")
            assert "{task}" in template

    asset_text = json.dumps(templates, ensure_ascii=False)
    assert_contains_all(
        asset_text,
        (
            "hidden-buttons-only",
            "login-as-only",
            "Okta-happy-path-only",
            "sandbox-approved-only",
            "revoked-key negative",
            "prompt asset ownership",
            "happy-path-webhook-only",
            "database-constraint-only",
            "cron-only",
            "green-index-job-only",
            "single-score-only",
            "last-write-wins",
            "# Authorization Policy Workflow Notes",
            "# Payment Webhook Workflow Notes",
            "# Search Index Consistency Workflow Notes",
            "# Search Quality Workflow Notes",
            "# Collaborative Conflict Resolution Workflow Notes",
        ),
    )

    helper_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_scaffold_templates.py").read_text(encoding="utf-8")
    trust_sources = "\n".join(
        (
            (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_scaffolds_trust_access.py").read_text(encoding="utf-8"),
            (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_scaffolds_trust_governance.py").read_text(encoding="utf-8"),
            (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_scaffolds_trust_secrets.py").read_text(encoding="utf-8"),
        )
    )
    assert "task-spec-scaffold-templates.json" in helper_source
    assert "apply_task_spec_scaffold_template_from_asset" in trust_sources
    product_sources = "\n".join(
        (
            (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_scaffolds_product_engagement.py").read_text(encoding="utf-8"),
            (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_scaffolds_product_operations.py").read_text(encoding="utf-8"),
            (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_scaffolds_product_search_ai.py").read_text(encoding="utf-8"),
        )
    )
    assert "apply_task_spec_scaffold_template_from_asset" in product_sources
    commercial_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_spec_scaffolds_commercial.py").read_text(encoding="utf-8")
    assert "apply_task_spec_scaffold_template_from_asset" in commercial_source
    for snippet in (
        "hidden-buttons-only",
        "login-as-only",
        "Okta-happy-path-only",
        "sandbox-approved-only",
        "revoked-key negative",
        "prompt asset ownership",
        "happy-path-webhook-only",
        "database-constraint-only",
        "cron-only",
        "green-index-job-only",
        "single-score-only",
        "last-write-wins",
    ):
        assert snippet not in trust_sources
        assert snippet not in product_sources
        assert snippet not in commercial_source


def test_task_visible_scaffold_copy_lives_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    visible_scaffolds = assets.task_visible_scaffolds
    assert set(visible_scaffolds) >= {
        "data_residency",
        "dispute_chargeback_lifecycle",
        "key_rotation",
        "kyc_aml_screening",
        "metric_reporting_reconciliation",
        "payout_settlement_reconciliation",
        "schedule_phase",
        "support_impersonation",
    }
    assert set(visible_scaffolds["data_residency"]) == {"en", "zh", "es"}
    assert visible_scaffolds["data_residency"]["en"]["metadata_name"] == "Data Residency Isolation Loop"
    assert "cron-only" in visible_scaffolds["schedule_phase"]["en"]["collaboration_summary"]
    assert "shared-admin-token" in visible_scaffolds["support_impersonation"]["en"]["collaboration_summary"]
    assert "Metric Contract Inspector" in visible_scaffolds["metric_reporting_reconciliation"]["en"]["spec_markdown"]
    assert "{success_focus}" in visible_scaffolds["payout_settlement_reconciliation"]["en"]["spec_markdown"]

    helper_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_visible_scaffold_assets.py").read_text(encoding="utf-8")
    commercial_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_visible_scaffolds_commercial.py").read_text(encoding="utf-8")
    trust_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_visible_scaffolds_trust.py").read_text(encoding="utf-8")
    product_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_visible_scaffolds_product.py").read_text(encoding="utf-8")
    assert "task-visible-scaffolds.json" in helper_source
    assert "apply_task_visible_scaffold_template_from_asset" in commercial_source
    assert "apply_task_visible_scaffold_from_asset" in trust_source
    assert "apply_task_visible_scaffold_from_asset" in product_source
    for snippet in (
        "Data Residency Isolation Loop",
        "Metric Contract Inspector",
        "cron-only",
        "shared-admin-token",
    ):
        assert snippet not in commercial_source
        assert snippet not in trust_source
        assert snippet not in product_source


def test_localized_base_bundle_overrides_live_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    overrides = assets.localized_base_bundle_overrides["locales"]
    asset_text = (REPO_ROOT / "src" / "loopora" / "assets" / "alignment" / "localized-base-bundle-overrides.yml").read_text(encoding="utf-8")
    assert set(overrides) >= {"zh"}
    zh = overrides["zh"]
    assert zh["metadata_name"] == "对齐 Starter Bundle"
    assert zh["roles"]["builder"]["name"] == "聚焦 Builder"
    assert "谨慎构建聚焦 starter slice" in zh["roles"]["builder"]["prompt_markdown"]
    assert "{builder_governance}" in zh["roles"]["builder"]["prompt_markdown"]

    localized_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_localized_variants.py").read_text(encoding="utf-8")
    localized_asset_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_localized_assets.py").read_text(encoding="utf-8")
    assert "localized-base-bundle-overrides.yml" in localized_asset_source
    assert "apply_localized_base_bundle_overrides" in localized_source
    for snippet in (
        "将工作协议投影到 spec",
        "谨慎构建聚焦 starter slice",
        "对齐 Starter Bundle",
    ):
        assert snippet in asset_text
        assert snippet not in localized_source


def test_improvement_bundle_fixture_copy_lives_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    fixtures = assets.improvement_bundle_fixtures["fixtures"]
    asset_text = (REPO_ROOT / "src" / "loopora" / "assets" / "alignment" / "improvement-bundle-fixtures.yml").read_text(encoding="utf-8")
    assert set(fixtures) >= {"search_refactor_improvement"}
    fixture = fixtures["search_refactor_improvement"]
    assert fixture["metadata_name"] == "Search 重构改进 Bundle"
    assert fixture["workflow"]["preset"] == "search-refactor-improvement-long-chain"
    assert fixture["workflow"]["steps"][-1]["inputs"]["evidence_query"]["verifies"] == [
        "task-scoped-refactor",
        "complexity-moved",
        "behavior-regression",
        "evidence-path",
        "local-governance",
    ]

    improvement_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_improvement_variants.py").read_text(encoding="utf-8")
    improvement_asset_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_improvement_assets.py").read_text(encoding="utf-8")
    assert "improvement-bundle-fixtures.yml" in improvement_asset_source
    assert "apply_alignment_improvement_bundle_fixture" in improvement_source
    for snippet in (
        "修订来源 Search Loop",
        "复杂度只是移动到另一个阶段",
        "search-refactor-improvement-long-chain",
    ):
        assert snippet in asset_text
        assert snippet not in improvement_source


def test_refund_bundle_fixture_copy_lives_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    fixtures = assets.refund_bundle_fixtures["fixtures"]
    asset_text = (REPO_ROOT / "src" / "loopora" / "assets" / "alignment" / "refund-bundle-fixtures.yml").read_text(encoding="utf-8")
    assert set(fixtures) >= {"refund_repair_en", "refund_repair_zh"}
    assert fixtures["refund_repair_en"]["metadata_name"] == "Refund Safety Repair Bundle"
    assert fixtures["refund_repair_zh"]["metadata_name"] == "退款安全修复 Bundle"
    assert fixtures["refund_repair_en"]["workflow"]["preset"] == "refund_repair_review"
    assert fixtures["refund_repair_zh"]["workflow"]["steps"][-1]["inputs"]["evidence_query"]["verifies"] == [
        "refund.authorization",
        "refund.audit",
        "refund.provider_failure",
        "refund.repair",
    ]

    refund_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_refund_variants.py").read_text(encoding="utf-8")
    refund_asset_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_refund_assets.py").read_text(encoding="utf-8")
    variant_asset_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_variant_assets.py").read_text(encoding="utf-8")
    assert "refund-bundle-fixtures.yml" in refund_asset_source
    assert "alignment_bundle_variant_fixtures_from_asset" in refund_asset_source
    assert "def apply_alignment_bundle_variant_fixture" in variant_asset_source
    assert "apply_alignment_refund_bundle_fixture" in refund_source
    for snippet in (
        "Ship a governed refund self-service path",
        "为退款用户、授权客户管理员、客服和财务交付受治理的退款自助路径",
        "refund_repair_review",
    ):
        assert snippet in asset_text
        assert snippet not in refund_source


def test_agreement_readiness_evidence_asset_keys_have_compatibility_factories() -> None:
    asset = json.loads((REPO_ROOT / "src" / "loopora" / "assets" / "alignment" / "agreement-readiness-evidence.json").read_text(encoding="utf-8"))
    factories = dict(agreement_evidence_module.AGREEMENT_READINESS_EVIDENCE_FACTORIES)
    assert set(factories) == set(asset["tasks"])
    assert "refund_repair" in factories
    assert "search_refactor_improvement" in factories
    assert "final production and finance feedback arrives too late" in asset["tasks"]["refund_repair"]["en"]["loop_fit"]
    assert "退款任务适合 Loopora" in asset["tasks"]["refund_repair"]["zh"]["loop_fit"]
    assert "complexity merely moved sideways" in asset["tasks"]["search_refactor_improvement"]["en"]["loop_fit"]
    assert "不把反馈扩展成开放式平台重写" in asset["tasks"]["search_refactor_improvement"]["zh"]["task_scope"]
    agreement_responses_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_agreement_responses.py").read_text(encoding="utf-8")
    improvement_responses_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_agreement_improvement_responses.py").read_text(encoding="utf-8")
    refund_responses_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_agreement_refund_responses.py").read_text(encoding="utf-8")
    assert "_refund_repair_readiness_evidence" in refund_responses_source
    assert "_search_refactor_improvement_readiness_evidence" in improvement_responses_source
    for snippet in (
        "final production and finance feedback arrives too late",
        "退款任务适合 Loopora",
        "complexity merely moved sideways",
        "不把反馈扩展成开放式平台重写",
    ):
        assert snippet not in agreement_responses_source
        assert snippet not in refund_responses_source
        assert snippet not in improvement_responses_source
    for fixture_key, function_name in factories.items():
        readiness_evidence = getattr(agreement_evidence_module, function_name)
        assert callable(readiness_evidence)
        assert readiness_evidence("Contract Task", language="en") == agreement_evidence_module._agreement_readiness_evidence_from_asset(
            fixture_key,
            "Contract Task",
            language="en",
        )


def test_readiness_issue_fixture_copy_lives_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    issue_fixtures = assets.readiness_issue_fixtures["issues"]
    asset_text = json.dumps(issue_fixtures, ensure_ascii=False)
    assert set(issue_fixtures) >= {
        "alignment_vague_loop_fit_readiness_evidence",
        "alignment_global_persona_readiness_evidence",
        "alignment_workflow_shape_without_gatekeeper_readiness_evidence",
    }
    for scenario, fixture in issue_fixtures.items():
        assert fixture["field"] in ALIGNMENT_READINESS_EVIDENCE_KEYS
        assert isinstance(fixture["evidence_text"], str)
        assert fixture["assistant_message"].strip()
        assert readiness_payload_module.alignment_readiness_issue_for_scenario(scenario) == (
            fixture["field"],
            fixture["evidence_text"],
            fixture["assistant_message"],
        )

    missing_evidence = readiness_payload_module.alignment_missing_readiness_evidence()
    assert set(missing_evidence) == {*ALIGNMENT_READINESS_EVIDENCE_KEYS, "open_questions"}
    readiness_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_readiness_payloads.py").read_text(encoding="utf-8")
    assert "readiness-issue-fixtures.json" in readiness_source
    for snippet in (
        "This is a complex and important task with many parts to handle well.",
        "Always remember the user's global preference memory",
        "我生成了 bundle，但 workflow 没说明最终裁决或收束节点。",
    ):
        assert snippet in asset_text
        assert snippet not in readiness_source


def test_preconfirmation_scenario_fixture_copy_lives_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    fixtures = assets.preconfirmation_fixtures
    scenario_payloads = fixtures["scenario_payloads"]
    agreement_overrides = fixtures["agreement_overrides"]
    asset_text = json.dumps(fixtures, ensure_ascii=False)
    assert set(scenario_payloads) >= {
        "alignment_question",
        "alignment_not_fit",
        "alignment_premature_bundle",
    }
    assert set(agreement_overrides) >= {
        "alignment_hidden_agreement_message",
        "alignment_survive_chat_loop_fit_readiness_evidence",
        "alignment_governance_markers_listed_without_responsibilities",
    }
    request = preconfirmation_payload_module.AlignmentPreconfirmationPayloadRequest(
        mode="normal",
        alignment_stage="clarifying",
        workdir=str(REPO_ROOT),
        prefers_chinese=True,
        is_improvement=False,
    )
    question_payload = preconfirmation_payload_module.alignment_preconfirmation_payload_for_scenario("alignment_question", request=request)
    assert question_payload["assistant_message"] == scenario_payloads["alignment_question"]["assistant_message"]
    assert question_payload["decision_options"][0]["id"] == "evidence_first"
    premature_payload = preconfirmation_payload_module.alignment_preconfirmation_payload_for_scenario("alignment_premature_bundle", request=request)
    assert premature_payload["status"] == "bundle"
    assert premature_payload["alignment_phase"] == "clarifying"
    governance_payload = preconfirmation_payload_module.alignment_preconfirmation_payload_for_scenario(
        "alignment_governance_markers_listed_without_responsibilities",
        request=request,
    )
    assert (
        governance_payload["readiness_evidence"]["workdir_facts"]
        == agreement_overrides["alignment_governance_markers_listed_without_responsibilities"]["readiness_evidence"]["workdir_facts"]
    )

    preconfirmation_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_preconfirmation_payloads.py").read_text(encoding="utf-8")
    assert "preconfirmation-scenario-fixtures.json" in preconfirmation_source
    for snippet in (
        "我建议先按",
        "What evidence should prove completion",
        "This is not one Agent pass plus human review",
    ):
        assert snippet in asset_text
        assert snippet not in preconfirmation_source


def test_bundle_scenario_fixture_copy_lives_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    scenario_payloads = assets.bundle_scenario_fixtures["scenario_payloads"]
    asset_text = json.dumps(scenario_payloads, ensure_ascii=False)
    assert set(scenario_payloads) >= {
        "alignment_invalid",
        "alignment_chinese_readiness_evidence",
        "alignment_generated_lineage_metadata",
        "alignment_missing_readiness_evidence",
        "alignment_refund_agreement_repair_bundle",
        "alignment_chinese_refund_agreement_repair_bundle",
    }
    request = SimpleNamespace(
        extra_context={"alignment_mode": "normal", "alignment_stage": "confirmed"},
        workdir=str(REPO_ROOT),
        prompt="General alignment task",
    )
    invalid_payload = alignment_payload_module.build_alignment_payload("alignment_invalid", request)
    assert invalid_payload["assistant_message"] == scenario_payloads["alignment_invalid"]["assistant_message"]
    assert "Broken Alignment Bundle" in invalid_payload["bundle_yaml"]
    chinese_payload = alignment_payload_module.build_alignment_payload("alignment_chinese_readiness_evidence", request)
    assert chinese_payload["agreement_summary"] == scenario_payloads["alignment_chinese_readiness_evidence"]["agreement_summary"]
    missing_payload = alignment_payload_module.build_alignment_payload("alignment_missing_readiness_evidence", request)
    assert set(missing_payload["readiness_evidence"]) == {*ALIGNMENT_READINESS_EVIDENCE_KEYS, "open_questions"}
    repair_request = SimpleNamespace(
        extra_context={"alignment_mode": "repair", "alignment_stage": "confirmed"},
        workdir=str(REPO_ROOT),
        prompt="General alignment task",
    )
    repair_payload = alignment_payload_module.build_alignment_payload("alignment_invalid_then_valid", repair_request)
    assert "Broken Alignment Bundle" not in repair_payload["bundle_yaml"]
    refund_payload = alignment_payload_module.build_alignment_payload("alignment_refund_agreement_repair_bundle", request)
    assert refund_payload["assistant_message"] == scenario_payloads["alignment_refund_agreement_repair_bundle"]["assistant_message"]
    assert "Refund Safety Repair Bundle" in refund_payload["bundle_yaml"]
    assert all(refund_payload["readiness_checklist"].values())
    chinese_refund_payload = alignment_payload_module.build_alignment_payload("alignment_chinese_refund_agreement_repair_bundle", request)
    assert chinese_refund_payload["assistant_message"] == scenario_payloads["alignment_chinese_refund_agreement_repair_bundle"]["assistant_message"]
    assert "退款安全修复 Bundle" in chinese_refund_payload["bundle_yaml"]
    assert all(chinese_refund_payload["readiness_checklist"].values())

    payloads_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_payloads.py").read_text(encoding="utf-8")
    assert "bundle-scenario-fixtures.json" in payloads_source
    for snippet in (
        "我先给出一个故意不完整的 bundle。",
        "I prepared a bundle but encoded source lineage metadata.",
        "我勾选了 checklist 但没有给出具体证据。",
        "I prepared a refund governance Loopora bundle with a Guide repair pass.",
        "已整理成一个包含 Guide 修复轮次的退款治理 Loopora bundle。",
    ):
        assert snippet in asset_text
        assert snippet not in payloads_source


def test_task_specific_role_fixture_prompt_fragments_live_in_alignment_asset() -> None:
    assets = load_alignment_guidance_assets()
    asset_text = json.dumps(assets.task_role_fixtures, ensure_ascii=False)
    task_fixtures = assets.task_role_fixtures["tasks"]
    predicate_routed_fixture_keys = {replacement.fixture_key for replacement in task_role_module.TASK_ROLE_FIXTURE_REPLACERS}
    assert predicate_routed_fixture_keys == set(task_fixtures) - {
        "generic_task_anchor",
        "refund_repair",
        "search_refactor_improvement",
    }
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
    task_roles_source = (REPO_ROOT / "src" / "loopora" / "executor_alignment_bundle_task_roles.py").read_text(encoding="utf-8")
    assert "TASK_ROLE_FIXTURE_REPLACERS" in task_roles_source
    assert "TaskRoleFixtureReplacement" in task_roles_source
    assert "def _task_anchored_role_replacers" not in task_roles_source
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
