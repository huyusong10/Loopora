from __future__ import annotations

import json
import time
from pathlib import Path


from loopora.bundles import bundle_to_yaml
from strategy_source_architecture_test_support import REPO_ROOT, design_boundary_source, loopora_source

RUN_REVISION_MISSING_CHECK_COUNT = 2


def _wait_for_status(service, session_id: str, *statuses: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    expected = set(statuses)
    while True:
        session = service.get_alignment_session(session_id)
        if session["status"] in expected:
            return session
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.05, remaining))
    raise AssertionError(f"alignment session stayed in {session['status']}, expected {sorted(expected)}")


def _confirm_alignment_agreement(service, session_id: str, *final_statuses: str) -> dict:
    agreement = _wait_for_status(service, session_id, "waiting_user")
    assert agreement["alignment_stage"] == "agreement_ready"
    assert agreement["working_agreement"]["summary"]
    for evidence_key in ("loop_fit", "task_scope", "residual_risk_policy", "local_governance"):
        assert agreement["working_agreement"]["readiness_evidence"][evidence_key]
    service.append_alignment_message(session_id, "确认")
    confirmed = _wait_for_status(service, session_id, *(final_statuses or ("ready",)))
    assert confirmed["working_agreement"]["readiness_checklist"]["explicit_confirmation"] is True
    return confirmed


def _assert_alignment_stage_blocked(service, session_id: str) -> None:
    assert any(event["event_type"] == "alignment_stage_blocked" for event in service.list_alignment_events(session_id))


def _assert_alignment_stage_blocked_for_key(service, session_id: str, key: str) -> None:
    events = service.list_alignment_events(session_id)
    assert any(
        event["event_type"] == "alignment_stage_blocked" and (key in event["payload"].get("missing", []) or key in event["payload"].get("error", ""))
        for event in events
    )


def _bundle_invocation_dir(artifact_root: Path) -> Path:
    bundle_invocations: list[Path] = []
    for invocation_dir in sorted((artifact_root / "invocations").iterdir()):
        output_path = invocation_dir / "output.json"
        if not output_path.is_file():
            continue
        try:
            output = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if output.get("bundle_written") is True:
            bundle_invocations.append(invocation_dir)
    if not bundle_invocations:
        raise AssertionError("no bundle-writing alignment invocation was recorded")
    return bundle_invocations[-1]


def _assert_run_succeeds_and_joins(service, run_id: str, *, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    run = service.get_run(run_id)
    thread = service._threads.get(run_id)
    while time.monotonic() < deadline:
        run = service.get_run(run_id)
        if run["status"] in {"succeeded", "failed", "stopped"}:
            break
        remaining = max(0.0, deadline - time.monotonic())
        if thread is not None:
            thread.join(timeout=min(0.05, remaining))
        else:
            time.sleep(min(0.05, remaining))
    run = service.get_run(run_id)
    thread_state = "absent" if thread is None else ("alive" if thread.is_alive() else "exited")
    assert run["status"] == "succeeded", f"run {run_id} ended as {run['status']!r} after {timeout:.1f}s; thread={thread_state}"


def _assert_alignment_preview_control_summary(preview: dict) -> None:
    control_summary = preview["control_summary"]
    assert control_summary["gatekeeper"]["requires_evidence_refs"] is True
    assert control_summary["coverage"]["check_count"] >= 1
    assert control_summary["coverage"]["target_count"] >= control_summary["coverage"]["check_count"]
    assert any(target["id"].startswith("done_when.") for target in control_summary["coverage"]["targets"])
    assert any("fail closed" in item for item in control_summary["residual_risk_policy"])
    assert any("smaller proven flow" in item for item in control_summary["judgment_tradeoffs"])
    assert any("Focused Builder (builder): Keep implementation narrow" in item for item in control_summary["role_postures"])
    assert any("final feedback is too slow to be the only control signal" in item for item in control_summary["loop_fit_reasons"])
    assert any("weak-proof control points" in item for item in control_summary["loop_fit_reasons"])
    assert preview["traceability"] == control_summary["traceability"]
    assert any(item["key"] == "loop_fit" and item["mapped"] for item in preview["traceability"]["items"])
    assert any(item["key"] == "coverage_targets" and item["mapped"] for item in preview["traceability"]["items"])
    assert any(item["key"] == "judgment_tradeoffs" and item["mapped"] for item in preview["traceability"]["items"])
    assert preview["traceability"]["mapped_count"] == preview["traceability"]["required_count"]


def _create_alignment_improvement_source_bundle(
    service,
    sample_spec_file: Path,
    sample_workdir: Path,
    *,
    completion_mode: str = "gatekeeper",
) -> dict:
    loop = service.create_loop(
        name="Improvement Source Loop",
        spec_path=sample_spec_file,
        workdir=sample_workdir,
        model="gpt-5.4-mini",
        reasoning_effort="medium",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
        completion_mode=completion_mode,
    )
    return service.import_bundle_text(
        bundle_to_yaml(
            service.derive_bundle_from_loop(
                loop["id"],
                name="Improvement Source Bundle",
                description="Start from an existing bundle.",
                collaboration_summary="Prefer evidence before changing posture.",
            )
        )
    )


def _write_run_revision_coverage(coverage_path: Path) -> None:
    coverage_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "ledger_path": "evidence/ledger.jsonl",
                "coverage_path": "evidence/coverage.json",
                "status": "partial",
                "summary": {"reason": "Required refund audit and payment failure checks still lack direct proof."},
                "evidence_count": 4,
                "check_count": 3,
                "covered_check_count": 1,
                "missing_check_count": 2,
                "covered_check_ids": ["check_permission"],
                "missing_check_ids": ["check_payment_failure", "check_audit_trail"],
                "target_count": 6,
                "covered_target_count": 2,
                "weak_target_count": 1,
                "missing_target_count": 2,
                "blocked_target_count": 1,
                "top_gaps": [
                    {
                        "target_id": "done_when.check_payment_failure",
                        "text": "Payment failure handoff has no direct proof.",
                    },
                    {
                        "target_id": "done_when.check_audit_trail",
                        "text": "Audit trail cannot yet reconstruct a refund.",
                    },
                ],
                "evidence_kind_counts": {"artifact": 2, "summary": 2},
                "artifact_ref_count": 2,
                "residual_risk_count": 1,
                "risk_signals": ["Payment provider retry path remains visible."],
                "latest_gatekeeper": {"id": "ev_gatekeeper", "result": "blocked"},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _assert_run_revision_coverage_agreement(agreement: dict) -> None:
    coverage_summary = agreement["source"]["coverage_summary"]
    assert coverage_summary["ledger_path"] == "evidence/ledger.jsonl"
    assert coverage_summary["coverage_path"] == "evidence/coverage.json"
    assert coverage_summary["covered_check_count"] == 1
    assert coverage_summary["missing_check_count"] == RUN_REVISION_MISSING_CHECK_COUNT
    assert coverage_summary["covered_check_ids"] == ["check_permission"]
    assert coverage_summary["missing_check_ids"] == ["check_payment_failure", "check_audit_trail"]
    assert coverage_summary["weak_target_count"] == 1
    assert coverage_summary["blocked_target_count"] == 1
    assert coverage_summary["risk_signals"] == ["Payment provider retry path remains visible."]
    assert any(item["artifact_refs"] for item in agreement["source"]["evidence_summary"])
    assert agreement["source"]["task_verdict"]["status"]
    assert "gatekeeper_verdict" in agreement["source"]
    assert agreement["source"]["gatekeeper_verdict"]["decision_summary"]


def _assert_run_revision_context_text(context_text: str, run: dict, agreement: dict) -> None:
    assert f"Source run status: {run['status']}" in context_text
    assert "Artifact paths:" in context_text
    assert "evidence/task_verdict.json" in context_text
    assert "Frozen judgment contract:" in context_text
    assert "Use GateKeeper evidence to improve the plan." in context_text
    assert "Repair evidence gaps before broad polishing." in context_text
    assert "GateKeeper treats skipped AGENTS.md evidence as Blocking." in context_text
    assert "`execution_strategy` should say what the next version should build" in context_text
    assert "`local_governance` should preserve or revise project-local governance responsibilities" in context_text
    assert f'"missing_check_count": {RUN_REVISION_MISSING_CHECK_COUNT}' in context_text
    assert "check_payment_failure" in context_text
    assert "Payment failure handoff has no direct proof." in context_text
    assert "Payment provider retry path remains visible." in context_text
    assert "Task verdict:" in context_text
    assert agreement["source"]["task_verdict"]["status"] in context_text
    assert "GateKeeper verdict:" in context_text
    assert "decision_summary" in context_text


def _agreement_response_boundary_sources() -> dict[str, str]:
    service_boundaries_path = REPO_ROOT / "design" / "service-boundaries.md"
    return {
        "responses": loopora_source("executor_alignment_agreement_responses.py"),
        "dispatch": loopora_source("executor_alignment_agreement_task_dispatch.py"),
        "dispatch_catalog": loopora_source("executor_alignment_agreement_task_dispatch_catalog.py"),
        "dispatch_commercial": loopora_source("executor_alignment_agreement_task_dispatch_commercial.py"),
        "dispatch_data": loopora_source("executor_alignment_agreement_task_dispatch_data.py"),
        "dispatch_operations": loopora_source("executor_alignment_agreement_task_dispatch_operations.py"),
        "dispatch_product": loopora_source("executor_alignment_agreement_task_dispatch_product.py"),
        "dispatch_trust": loopora_source("executor_alignment_agreement_task_dispatch_trust.py"),
        "dispatch_types": loopora_source("executor_alignment_agreement_task_dispatch_types.py"),
        "task_responses": loopora_source("executor_alignment_agreement_task_responses.py"),
        "improvement_responses": loopora_source("executor_alignment_agreement_improvement_responses.py"),
        "refund_responses": loopora_source("executor_alignment_agreement_refund_responses.py"),
        "commercial_responses": loopora_source("executor_alignment_agreement_task_responses_commercial.py"),
        "commercial_billing_responses": loopora_source("executor_alignment_agreement_task_responses_commercial_billing.py"),
        "commercial_metrics_responses": loopora_source("executor_alignment_agreement_task_responses_commercial_metrics.py"),
        "commercial_payments_responses": loopora_source("executor_alignment_agreement_task_responses_commercial_payments.py"),
        "data_responses": loopora_source("executor_alignment_agreement_task_responses_data.py"),
        "data_ingest_responses": loopora_source("executor_alignment_agreement_task_responses_data_ingest.py"),
        "data_lifecycle_responses": loopora_source("executor_alignment_agreement_task_responses_data_lifecycle.py"),
        "data_migration_responses": loopora_source("executor_alignment_agreement_task_responses_data_migration.py"),
        "data_resilience_responses": loopora_source("executor_alignment_agreement_task_responses_data_resilience.py"),
        "operations_responses": loopora_source("executor_alignment_agreement_task_responses_operations.py"),
        "operations_collaboration_responses": loopora_source("executor_alignment_agreement_task_responses_operations_collaboration.py"),
        "operations_incident_responses": loopora_source("executor_alignment_agreement_task_responses_operations_incident.py"),
        "operations_release_responses": loopora_source("executor_alignment_agreement_task_responses_operations_release.py"),
        "product_responses": loopora_source("executor_alignment_agreement_task_responses_product.py"),
        "product_engagement_responses": loopora_source("executor_alignment_agreement_task_responses_product_engagement.py"),
        "product_operations_responses": loopora_source("executor_alignment_agreement_task_responses_product_operations.py"),
        "product_search_ai_responses": loopora_source("executor_alignment_agreement_task_responses_product_search_ai.py"),
        "trust_responses": loopora_source("executor_alignment_agreement_task_responses_trust.py"),
        "trust_access_responses": loopora_source("executor_alignment_agreement_task_responses_trust_access.py"),
        "trust_access_authorization_responses": loopora_source("executor_alignment_agreement_task_responses_trust_access_authorization.py"),
        "trust_access_breakglass_responses": loopora_source("executor_alignment_agreement_task_responses_trust_access_breakglass.py"),
        "trust_access_identity_responses": loopora_source("executor_alignment_agreement_task_responses_trust_access_identity.py"),
        "trust_governance_responses": loopora_source("executor_alignment_agreement_task_responses_trust_governance.py"),
        "trust_secrets_responses": loopora_source("executor_alignment_agreement_task_responses_trust_secrets.py"),
        "contracts": design_boundary_source(),
        "service_boundaries": service_boundaries_path.read_text(encoding="utf-8"),
    }


def _assert_agreement_task_dispatch_boundary(sources: dict[str, str]) -> None:
    assert "from loopora.executor_alignment_agreement_task_dispatch import" in sources["responses"]
    assert "from loopora import executor_alignment_agreement_task_responses as task_responses" in sources["dispatch"]
    assert "from loopora.executor_alignment_agreement_task_dispatch_catalog import TASK_AGREEMENT_FACTORIES" in sources["dispatch"]
    assert "from loopora.executor_alignment_agreement_predicates import" not in sources["dispatch"]
    for domain_response_import in (
        "executor_alignment_agreement_task_responses_commercial",
        "executor_alignment_agreement_task_responses_data",
        "executor_alignment_agreement_task_responses_operations",
        "executor_alignment_agreement_task_responses_product",
        "executor_alignment_agreement_task_responses_trust",
    ):
        assert domain_response_import not in sources["dispatch"]
    assert "def alignment_task_anchored_agreement_response" in sources["dispatch"]
    assert "for predicate, factories in TASK_AGREEMENT_FACTORIES" in sources["dispatch"]
    for dispatch_marker in ("def _localized_task_agreement_response",):
        assert dispatch_marker in sources["dispatch"]
        assert dispatch_marker not in sources["responses"]
    for catalog_marker in (
        "TASK_AGREEMENT_FACTORIES",
        'TRUST_TASK_AGREEMENT_FACTORY_ROUTES["prompt_asset_ownership"]',
        'DATA_TASK_AGREEMENT_FACTORY_ROUTES["data_import_validation"]',
        'COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES["payment_webhook_ledger"]',
        'PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES["rag_long_chain"]',
        'OPERATIONS_TASK_AGREEMENT_FACTORY_ROUTES["feature_flag_rollout"]',
    ):
        assert catalog_marker in sources["dispatch_catalog"]
        assert catalog_marker not in sources["responses"]
    dispatch_body_markers_by_owner = {
        "dispatch_product": (
            "product_task_responses.alignment_english_rag_long_chain_agreement_response",
            "PRODUCT_TASK_AGREEMENT_FACTORY_ROUTES",
        ),
        "dispatch_commercial": (
            "commercial_task_responses.alignment_chinese_payment_webhook_ledger_agreement_response",
            "COMMERCIAL_TASK_AGREEMENT_FACTORY_ROUTES",
        ),
        "dispatch_data": (
            "data_task_responses.alignment_chinese_data_import_validation_agreement_response",
            "DATA_TASK_AGREEMENT_FACTORY_ROUTES",
        ),
        "dispatch_operations": (
            "operations_task_responses.alignment_chinese_feature_flag_rollout_agreement_response",
            "OPERATIONS_TASK_AGREEMENT_FACTORY_ROUTES",
        ),
        "dispatch_trust": (
            "trust_task_responses.alignment_chinese_data_residency_agreement_response",
            "TRUST_TASK_AGREEMENT_FACTORY_ROUTES",
        ),
    }
    for owner_key, dispatch_markers in dispatch_body_markers_by_owner.items():
        assert "from loopora.executor_alignment_agreement_predicates import" in sources[owner_key]
        for dispatch_marker in dispatch_markers:
            assert dispatch_marker in sources[owner_key]
            assert dispatch_marker not in sources["dispatch"]
            assert dispatch_marker not in sources["responses"]


_DATA_AGREEMENT_RESPONSE_BODY_KEYS = (
    "data_ingest_responses",
    "data_lifecycle_responses",
    "data_migration_responses",
    "data_resilience_responses",
)
_PRODUCT_AGREEMENT_RESPONSE_BODY_KEYS = (
    "product_engagement_responses",
    "product_operations_responses",
    "product_search_ai_responses",
)
_TRUST_ACCESS_AGREEMENT_RESPONSE_BODY_KEYS = (
    "trust_access_authorization_responses",
    "trust_access_breakglass_responses",
    "trust_access_identity_responses",
)
_TRUST_AGREEMENT_RESPONSE_BODY_KEYS = (
    *_TRUST_ACCESS_AGREEMENT_RESPONSE_BODY_KEYS,
    "trust_governance_responses",
    "trust_secrets_responses",
)
_COMMERCIAL_AGREEMENT_RESPONSE_BODY_KEYS = (
    "commercial_billing_responses",
    "commercial_metrics_responses",
    "commercial_payments_responses",
)
_OPERATIONS_AGREEMENT_RESPONSE_BODY_KEYS = (
    "operations_collaboration_responses",
    "operations_incident_responses",
    "operations_release_responses",
)
_AGREEMENT_TASK_DISPATCH_BODY_KEYS = (
    "dispatch_commercial",
    "dispatch_data",
    "dispatch_operations",
    "dispatch_product",
    "dispatch_trust",
)
_AGREEMENT_TASK_DISPATCH_SOURCE_KEYS = (
    "dispatch",
    "dispatch_catalog",
    *_AGREEMENT_TASK_DISPATCH_BODY_KEYS,
    "dispatch_types",
)
_AGREEMENT_DOMAIN_RESPONSE_BODY_KEYS = (
    "improvement_responses",
    "refund_responses",
    *_COMMERCIAL_AGREEMENT_RESPONSE_BODY_KEYS,
    *_DATA_AGREEMENT_RESPONSE_BODY_KEYS,
    *_OPERATIONS_AGREEMENT_RESPONSE_BODY_KEYS,
    *_PRODUCT_AGREEMENT_RESPONSE_BODY_KEYS,
    *_TRUST_AGREEMENT_RESPONSE_BODY_KEYS,
)
_AGREEMENT_DOMAIN_RESPONSE_FACADE_KEYS = (
    "commercial_responses",
    "data_responses",
    "operations_responses",
    "product_responses",
    "trust_access_responses",
    "trust_responses",
)
_AGREEMENT_DOMAIN_RESPONSE_SOURCE_KEYS = (*_AGREEMENT_DOMAIN_RESPONSE_FACADE_KEYS, *_AGREEMENT_DOMAIN_RESPONSE_BODY_KEYS)
_AGREEMENT_RESPONSE_SOURCE_KEYS = (
    "task_responses",
    *_AGREEMENT_DOMAIN_RESPONSE_SOURCE_KEYS,
    *_AGREEMENT_TASK_DISPATCH_SOURCE_KEYS,
    "responses",
)


def _assert_agreement_response_marker_owned_by_source(sources: dict[str, str], marker: str, *, owner_key: str) -> None:
    assert marker in sources[owner_key]
    for source_key in _AGREEMENT_RESPONSE_SOURCE_KEYS:
        if source_key != owner_key:
            assert marker not in sources[source_key]


def _assert_agreement_task_response_domain_boundaries(sources: dict[str, str]) -> None:
    for response_marker in (
        "def _task_success_surface_evidence",
        "def _task_fake_done_risk_evidence",
        "agent_candidate_traceability_terms",
    ):
        _assert_agreement_response_marker_owned_by_source(sources, response_marker, owner_key="task_responses")
    _assert_commercial_agreement_task_response_boundaries(sources)
    _assert_data_agreement_task_response_boundaries(sources)
    _assert_operations_agreement_task_response_boundaries(sources)
    _assert_product_agreement_task_response_boundaries(sources)
    _assert_trust_agreement_task_response_boundaries(sources)
    assert "def _agreement_task_clause" in sources["task_responses"]
    for source_key in _AGREEMENT_DOMAIN_RESPONSE_SOURCE_KEYS:
        assert "def _agreement_task_clause" not in sources[source_key]


def _assert_data_agreement_task_response_boundaries(sources: dict[str, str]) -> None:
    response_markers_by_owner = {
        "data_ingest_responses": (
            "def alignment_chinese_data_import_validation_agreement_response",
            "def alignment_spanish_file_upload_storage_safety_agreement_response",
        ),
        "data_lifecycle_responses": (
            "def alignment_spanish_dsar_data_export_agreement_response",
            "def alignment_chinese_data_lifecycle_deletion_retention_agreement_response",
        ),
        "data_migration_responses": (
            "def alignment_chinese_database_schema_migration_agreement_response",
            "def alignment_english_cdc_replication_consistency_agreement_response",
        ),
        "data_resilience_responses": (
            "def alignment_english_backup_restore_recovery_agreement_response",
            "def alignment_spanish_audit_log_integrity_retention_agreement_response",
        ),
    }
    for owner_key, response_markers in response_markers_by_owner.items():
        for response_marker in response_markers:
            _assert_agreement_response_marker_owned_by_source(sources, response_marker, owner_key=owner_key)

    for export_marker in (
        "alignment_chinese_data_import_validation_agreement_response as alignment_chinese_data_import_validation_agreement_response",
        "alignment_english_backup_restore_recovery_agreement_response as alignment_english_backup_restore_recovery_agreement_response",
        "alignment_spanish_dsar_data_export_agreement_response as alignment_spanish_dsar_data_export_agreement_response",
    ):
        assert export_marker in sources["data_responses"]


def _assert_commercial_agreement_task_response_boundaries(sources: dict[str, str]) -> None:
    response_markers_by_owner = {
        "commercial_billing_responses": (
            "def alignment_english_usage_quota_metering_agreement_response",
            "def alignment_spanish_subscription_entitlement_billing_agreement_response",
            "def alignment_chinese_tax_calculation_compliance_agreement_response",
        ),
        "commercial_metrics_responses": ("def alignment_english_metric_reporting_reconciliation_agreement_response",),
        "commercial_payments_responses": (
            "def alignment_chinese_payment_webhook_ledger_agreement_response",
            "def alignment_spanish_payout_settlement_reconciliation_agreement_response",
            "def alignment_english_dispute_chargeback_lifecycle_agreement_response",
        ),
    }
    for owner_key, response_markers in response_markers_by_owner.items():
        for response_marker in response_markers:
            _assert_agreement_response_marker_owned_by_source(sources, response_marker, owner_key=owner_key)

    for export_marker in (
        "alignment_chinese_payment_webhook_ledger_agreement_response as alignment_chinese_payment_webhook_ledger_agreement_response",
        "alignment_english_metric_reporting_reconciliation_agreement_response as alignment_english_metric_reporting_reconciliation_agreement_response",
        "alignment_spanish_subscription_entitlement_billing_agreement_response as alignment_spanish_subscription_entitlement_billing_agreement_response",
    ):
        assert export_marker in sources["commercial_responses"]


def _assert_operations_agreement_task_response_boundaries(sources: dict[str, str]) -> None:
    response_markers_by_owner = {
        "operations_release_responses": (
            "def alignment_chinese_feature_flag_rollout_agreement_response",
            "def alignment_english_cache_invalidation_consistency_agreement_response",
        ),
        "operations_collaboration_responses": ("def alignment_english_concurrency_conflict_resolution_agreement_response",),
        "operations_incident_responses": ("def alignment_spanish_incident_root_cause_agreement_response",),
    }
    for owner_key, response_markers in response_markers_by_owner.items():
        for response_marker in response_markers:
            _assert_agreement_response_marker_owned_by_source(sources, response_marker, owner_key=owner_key)

    for export_marker in (
        "alignment_chinese_feature_flag_rollout_agreement_response as alignment_chinese_feature_flag_rollout_agreement_response",
        "alignment_english_cache_invalidation_consistency_agreement_response as alignment_english_cache_invalidation_consistency_agreement_response",
        "alignment_spanish_incident_root_cause_agreement_response as alignment_spanish_incident_root_cause_agreement_response",
    ):
        assert export_marker in sources["operations_responses"]


def _assert_product_agreement_task_response_boundaries(sources: dict[str, str]) -> None:
    response_markers_by_owner = {
        "product_search_ai_responses": (
            "def alignment_english_rag_long_chain_agreement_response",
            "def alignment_spanish_search_index_consistency_agreement_response",
        ),
        "product_operations_responses": (
            "def alignment_english_inventory_reservation_consistency_agreement_response",
            "def alignment_spanish_analytics_experiment_instrumentation_agreement_response",
        ),
        "product_engagement_responses": (
            "def alignment_chinese_notification_subscription_deliverability_agreement_response",
            "def alignment_english_support_ticket_sla_agreement_response",
            "def alignment_spanish_schedule_timezone_recurrence_agreement_response",
        ),
    }
    for owner_key, response_markers in response_markers_by_owner.items():
        for response_marker in response_markers:
            _assert_agreement_response_marker_owned_by_source(sources, response_marker, owner_key=owner_key)

    for export_marker in (
        "alignment_english_rag_long_chain_agreement_response as alignment_english_rag_long_chain_agreement_response",
        "alignment_chinese_notification_subscription_deliverability_agreement_response as alignment_chinese_notification_subscription_deliverability_agreement_response",
        "alignment_spanish_search_index_consistency_agreement_response as alignment_spanish_search_index_consistency_agreement_response",
    ):
        assert export_marker in sources["product_responses"]


def _assert_trust_agreement_task_response_boundaries(sources: dict[str, str]) -> None:
    _assert_trust_access_agreement_task_response_boundaries(sources)
    response_markers_by_owner = {
        "trust_governance_responses": (
            "def alignment_chinese_data_residency_agreement_response",
            "def alignment_spanish_kyc_aml_screening_agreement_response",
        ),
        "trust_secrets_responses": (
            "def alignment_english_key_rotation_agreement_response",
            "def alignment_chinese_prompt_asset_ownership_agreement_response",
        ),
    }
    for owner_key, response_markers in response_markers_by_owner.items():
        for response_marker in response_markers:
            _assert_agreement_response_marker_owned_by_source(sources, response_marker, owner_key=owner_key)

    for export_marker in (
        "alignment_chinese_data_residency_agreement_response as alignment_chinese_data_residency_agreement_response",
        "alignment_english_identity_sso_agreement_response as alignment_english_identity_sso_agreement_response",
        "alignment_spanish_authorization_policy_agreement_response as alignment_spanish_authorization_policy_agreement_response",
    ):
        assert export_marker in sources["trust_responses"]


def _assert_trust_access_agreement_task_response_boundaries(sources: dict[str, str]) -> None:
    response_markers_by_owner = {
        "trust_access_identity_responses": (
            "def alignment_english_identity_sso_agreement_response",
            "def alignment_english_auth_session_token_lifecycle_agreement_response",
        ),
        "trust_access_authorization_responses": ("def alignment_spanish_authorization_policy_agreement_response",),
        "trust_access_breakglass_responses": ("def alignment_chinese_support_impersonation_agreement_response",),
    }
    for owner_key, response_markers in response_markers_by_owner.items():
        for response_marker in response_markers:
            _assert_agreement_response_marker_owned_by_source(sources, response_marker, owner_key=owner_key)

    for export_marker in (
        "alignment_english_identity_sso_agreement_response as alignment_english_identity_sso_agreement_response",
        "alignment_spanish_authorization_policy_agreement_response as alignment_spanish_authorization_policy_agreement_response",
        "alignment_chinese_support_impersonation_agreement_response as alignment_chinese_support_impersonation_agreement_response",
    ):
        assert export_marker in sources["trust_access_responses"]


def _assert_agreement_task_response_design_inventory(sources: dict[str, str]) -> None:
    for module_name in (
        "executor_alignment_agreement_task_dispatch.py",
        "executor_alignment_agreement_task_dispatch_catalog.py",
        "executor_alignment_agreement_task_dispatch_commercial.py",
        "executor_alignment_agreement_task_dispatch_data.py",
        "executor_alignment_agreement_task_dispatch_operations.py",
        "executor_alignment_agreement_task_dispatch_product.py",
        "executor_alignment_agreement_task_dispatch_trust.py",
        "executor_alignment_agreement_task_dispatch_types.py",
        "executor_alignment_agreement_task_responses.py",
        "executor_alignment_agreement_task_responses_commercial.py",
        "executor_alignment_agreement_task_responses_commercial_billing.py",
        "executor_alignment_agreement_task_responses_commercial_metrics.py",
        "executor_alignment_agreement_task_responses_commercial_payments.py",
        "executor_alignment_agreement_task_responses_data.py",
        "executor_alignment_agreement_task_responses_data_ingest.py",
        "executor_alignment_agreement_task_responses_data_lifecycle.py",
        "executor_alignment_agreement_task_responses_data_migration.py",
        "executor_alignment_agreement_task_responses_data_resilience.py",
        "executor_alignment_agreement_task_responses_operations.py",
        "executor_alignment_agreement_task_responses_operations_collaboration.py",
        "executor_alignment_agreement_task_responses_operations_incident.py",
        "executor_alignment_agreement_task_responses_operations_release.py",
        "executor_alignment_agreement_task_responses_product.py",
        "executor_alignment_agreement_task_responses_product_engagement.py",
        "executor_alignment_agreement_task_responses_product_operations.py",
        "executor_alignment_agreement_task_responses_product_search_ai.py",
        "executor_alignment_agreement_task_responses_trust.py",
        "executor_alignment_agreement_task_responses_trust_access.py",
        "executor_alignment_agreement_task_responses_trust_access_authorization.py",
        "executor_alignment_agreement_task_responses_trust_access_breakglass.py",
        "executor_alignment_agreement_task_responses_trust_access_identity.py",
        "executor_alignment_agreement_task_responses_trust_governance.py",
        "executor_alignment_agreement_task_responses_trust_secrets.py",
    ):
        assert module_name in sources["contracts"]
        assert module_name in sources["service_boundaries"]


def _assert_agreement_evidence_import_boundary(sources: dict[str, str]) -> None:
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["task_responses"]
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["commercial_responses"]
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["data_responses"]
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["operations_responses"]
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["product_responses"]
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["trust_responses"]
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["trust_access_responses"]
    for source_key in _AGREEMENT_TASK_DISPATCH_SOURCE_KEYS:
        assert "from loopora.executor_alignment_agreement_evidence import" not in sources[source_key]
    for source_key in _AGREEMENT_DOMAIN_RESPONSE_BODY_KEYS:
        assert "from loopora.executor_alignment_agreement_evidence import" in sources[source_key]
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["dispatch"]
    assert "from loopora.executor_alignment_agreement_evidence import" not in sources["responses"]
    assert "agreement-readiness-evidence.json" in sources["evidence"]
    assert "def _agreement_readiness_evidence_from_asset" in sources["evidence"]
    assert "def _agreement_readiness_evidence_factory" in sources["evidence"]
    assert "AGREEMENT_READINESS_EVIDENCE_FACTORIES" in sources["evidence"]
    for marker, obsolete_marker in (
        ('("identity_sso", "_identity_sso_readiness_evidence")', "def _identity_sso_readiness_evidence"),
        ('("payment_webhook_ledger", "_payment_webhook_ledger_readiness_evidence")', "def _payment_webhook_ledger_readiness_evidence"),
        ('("auth_session_token_lifecycle", "_auth_session_token_lifecycle_readiness_evidence")', "def _auth_session_token_lifecycle_readiness_evidence"),
        ('("refund_repair", "_refund_repair_readiness_evidence")', "def _refund_repair_readiness_evidence"),
        ('("search_refactor_improvement", "_search_refactor_improvement_readiness_evidence")', "def _search_refactor_improvement_readiness_evidence"),
    ):
        assert marker in sources["evidence"]
        assert obsolete_marker not in sources["evidence"]
        assert obsolete_marker not in "\n".join(sources[key] for key in ("task_responses", *_AGREEMENT_DOMAIN_RESPONSE_SOURCE_KEYS, "dispatch", "responses"))
    assert "def _agreement_task_clause" in sources["task_responses"]
    assert "def _agreement_task_clause" not in sources["evidence"]
    for source_key in _AGREEMENT_DOMAIN_RESPONSE_SOURCE_KEYS:
        assert "def _agreement_task_clause" not in sources[source_key]
    assert "def _agreement_task_clause" not in sources["dispatch"]
    assert "def _agreement_task_clause" not in sources["responses"]


def _assert_agreement_readiness_asset_boundary(sources: dict[str, str], asset_text: str, asset: dict) -> None:
    assert set(asset["tasks"]["identity_sso"]) == {"en", "es", "zh"}
    assert set(asset["tasks"]["refund_repair"]) == {"en", "es", "zh"}
    assert set(asset["tasks"]["search_refactor_improvement"]) == {"en", "es", "zh"}
    assert "{task}" in asset["tasks"]["identity_sso"]["en"]["task_scope"]
    for snippet in (
        "enterprise SSO risk is proven through IdP metadata",
        "payment provider webhook ingestion and ledger reconciliation",
        "auth session/token lifecycle 的真实完成要通过",
        "final production and finance feedback arrives too late",
        "退款任务适合 Loopora",
        "不把反馈扩展成开放式平台重写",
        "complexity merely moved sideways",
    ):
        assert snippet in asset_text
        assert snippet not in sources["evidence"]
        assert snippet not in sources["task_responses"]
        for source_key in _AGREEMENT_DOMAIN_RESPONSE_SOURCE_KEYS:
            assert snippet not in sources[source_key]
        assert snippet not in sources["dispatch"]
        assert snippet not in sources["responses"]


def _assert_agreement_evidence_design_inventory(sources: dict[str, str]) -> None:
    for artifact_name in (
        "agreement-readiness-evidence.json",
        "executor_alignment_agreement_evidence.py",
        "executor_alignment_agreement_improvement_responses.py",
        "executor_alignment_agreement_refund_responses.py",
        "executor_alignment_agreement_task_dispatch.py",
        "executor_alignment_agreement_task_dispatch_catalog.py",
        "executor_alignment_agreement_task_dispatch_commercial.py",
        "executor_alignment_agreement_task_dispatch_data.py",
        "executor_alignment_agreement_task_dispatch_operations.py",
        "executor_alignment_agreement_task_dispatch_product.py",
        "executor_alignment_agreement_task_dispatch_trust.py",
        "executor_alignment_agreement_task_dispatch_types.py",
        "executor_alignment_agreement_task_responses.py",
        "executor_alignment_agreement_task_responses_commercial.py",
        "executor_alignment_agreement_task_responses_commercial_billing.py",
        "executor_alignment_agreement_task_responses_commercial_metrics.py",
        "executor_alignment_agreement_task_responses_commercial_payments.py",
        "executor_alignment_agreement_task_responses_data.py",
        "executor_alignment_agreement_task_responses_data_ingest.py",
        "executor_alignment_agreement_task_responses_data_lifecycle.py",
        "executor_alignment_agreement_task_responses_data_migration.py",
        "executor_alignment_agreement_task_responses_data_resilience.py",
        "executor_alignment_agreement_task_responses_operations.py",
        "executor_alignment_agreement_task_responses_operations_collaboration.py",
        "executor_alignment_agreement_task_responses_operations_incident.py",
        "executor_alignment_agreement_task_responses_operations_release.py",
        "executor_alignment_agreement_task_responses_product.py",
        "executor_alignment_agreement_task_responses_product_engagement.py",
        "executor_alignment_agreement_task_responses_product_operations.py",
        "executor_alignment_agreement_task_responses_product_search_ai.py",
        "executor_alignment_agreement_task_responses_trust.py",
        "executor_alignment_agreement_task_responses_trust_access.py",
        "executor_alignment_agreement_task_responses_trust_access_authorization.py",
        "executor_alignment_agreement_task_responses_trust_access_breakglass.py",
        "executor_alignment_agreement_task_responses_trust_access_identity.py",
        "executor_alignment_agreement_task_responses_trust_governance.py",
        "executor_alignment_agreement_task_responses_trust_secrets.py",
    ):
        assert artifact_name in sources["contracts"]
        assert artifact_name in sources["service_boundaries"]


__all__ = [
    "_agreement_response_boundary_sources",
    "_assert_agreement_evidence_design_inventory",
    "_assert_agreement_evidence_import_boundary",
    "_assert_agreement_readiness_asset_boundary",
    "_assert_agreement_task_dispatch_boundary",
    "_assert_agreement_task_response_design_inventory",
    "_assert_agreement_task_response_domain_boundaries",
    "_assert_alignment_preview_control_summary",
    "_assert_alignment_stage_blocked",
    "_assert_alignment_stage_blocked_for_key",
    "_assert_run_revision_context_text",
    "_assert_run_revision_coverage_agreement",
    "_assert_run_succeeds_and_joins",
    "_bundle_invocation_dir",
    "_confirm_alignment_agreement",
    "_create_alignment_improvement_source_bundle",
    "_wait_for_status",
    "_write_run_revision_coverage",
]
