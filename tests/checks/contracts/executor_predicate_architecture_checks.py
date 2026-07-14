from __future__ import annotations


def _assert_data_task_predicate_domain_boundaries(sources: dict[str, str]) -> None:
    data_predicate_markers_by_owner = {
        "data_resilience_task_predicates": (
            "def is_backup_restore_recovery_task",
            "def is_audit_log_integrity_retention_task",
        ),
        "data_migration_task_predicates": (
            "def is_database_schema_migration_task",
            "def is_cdc_replication_consistency_task",
        ),
        "data_lifecycle_task_predicates": (
            "def is_dsar_data_export_task",
            "def is_data_lifecycle_deletion_retention_task",
        ),
        "data_read_models_task_predicates": ("def is_cache_invalidation_consistency_task",),
        "data_ingest_task_predicates": (
            "def is_data_import_validation_task",
            "def is_file_upload_storage_safety_task",
        ),
    }
    data_predicate_body_keys = tuple(data_predicate_markers_by_owner)
    for owner_key, predicate_markers in data_predicate_markers_by_owner.items():
        for predicate_marker in predicate_markers:
            assert predicate_marker in sources[owner_key]
            assert predicate_marker not in sources["data_task_predicates"]
            assert predicate_marker not in sources["task_predicates"]
            assert predicate_marker not in sources["routing"]
            assert predicate_marker not in sources["variants"]
            for body_key in data_predicate_body_keys:
                if body_key != owner_key:
                    assert predicate_marker not in sources[body_key]


def _assert_commercial_task_predicate_domain_boundaries(sources: dict[str, str]) -> None:
    commercial_predicate_markers_by_owner = {
        "commercial_metrics_task_predicates": ("def is_metric_reporting_reconciliation_task",),
        "commercial_payments_task_predicates": (
            "def is_dispute_chargeback_lifecycle_task",
            "def is_payout_settlement_reconciliation_task",
            "def is_payment_webhook_ledger_task",
        ),
        "commercial_billing_task_predicates": (
            "def is_usage_quota_metering_task",
            "def is_subscription_entitlement_billing_task",
            "def is_tax_calculation_compliance_task",
        ),
    }
    commercial_predicate_body_keys = tuple(commercial_predicate_markers_by_owner)
    for owner_key, predicate_markers in commercial_predicate_markers_by_owner.items():
        for predicate_marker in predicate_markers:
            assert predicate_marker in sources[owner_key]
            assert predicate_marker not in sources["commercial_task_predicates"]
            assert predicate_marker not in sources["task_predicates"]
            assert predicate_marker not in sources["routing"]
            assert predicate_marker not in sources["variants"]
            for body_key in commercial_predicate_body_keys:
                if body_key != owner_key:
                    assert predicate_marker not in sources[body_key]


def _assert_product_task_predicate_domain_boundaries(sources: dict[str, str]) -> None:
    product_predicate_markers_by_owner = {
        "product_search_ai_task_predicates": (
            "def is_rag_long_chain_task",
            "def is_search_index_consistency_task",
            "def is_search_quality_task",
        ),
        "product_engagement_task_predicates": (
            "def is_schedule_phase_task",
            "def is_support_ticket_sla_task",
            "def is_notification_subscription_deliverability_task",
        ),
        "product_operations_task_predicates": (
            "def is_analytics_experiment_instrumentation_task",
            "def is_concurrency_conflict_resolution_task",
            "def is_inventory_reservation_consistency_task",
        ),
    }
    product_predicate_body_keys = tuple(product_predicate_markers_by_owner)
    for owner_key, predicate_markers in product_predicate_markers_by_owner.items():
        for predicate_marker in predicate_markers:
            assert predicate_marker in sources[owner_key]
            assert predicate_marker not in sources["product_task_predicates"]
            assert predicate_marker not in sources["task_predicates"]
            assert predicate_marker not in sources["routing"]
            assert predicate_marker not in sources["variants"]
            for body_key in product_predicate_body_keys:
                if body_key != owner_key:
                    assert predicate_marker not in sources[body_key]


def _assert_trust_task_predicate_domain_boundaries(sources: dict[str, str]) -> None:
    trust_predicate_markers_by_owner = {
        "trust_access_task_predicates": (
            "def is_auth_session_token_lifecycle_task",
            "def is_support_impersonation_task",
            "def is_identity_sso_task",
            "def is_authorization_policy_task",
        ),
        "trust_governance_task_predicates": (
            "def is_data_residency_task",
            "def is_kyc_aml_screening_task",
        ),
        "trust_secrets_task_predicates": (
            "def is_prompt_asset_ownership_task",
            "def is_key_rotation_task",
        ),
    }
    trust_predicate_body_keys = tuple(trust_predicate_markers_by_owner)
    for owner_key, predicate_markers in trust_predicate_markers_by_owner.items():
        for predicate_marker in predicate_markers:
            assert predicate_marker in sources[owner_key]
            assert predicate_marker not in sources["trust_task_predicates"]
            assert predicate_marker not in sources["task_predicates"]
            assert predicate_marker not in sources["routing"]
            assert predicate_marker not in sources["variants"]
            for body_key in trust_predicate_body_keys:
                if body_key != owner_key:
                    assert predicate_marker not in sources[body_key]
