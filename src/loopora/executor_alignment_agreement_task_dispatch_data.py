from __future__ import annotations

from loopora import executor_alignment_agreement_task_responses_data as data_task_responses
from loopora.executor_alignment_agreement_predicates import (
    _agreement_is_audit_log_integrity_retention_task,
    _agreement_is_backup_restore_recovery_task,
    _agreement_is_cdc_replication_consistency_task,
    _agreement_is_data_import_validation_task,
    _agreement_is_data_lifecycle_deletion_retention_task,
    _agreement_is_database_schema_migration_task,
    _agreement_is_dsar_data_export_task,
    _agreement_is_file_upload_storage_safety_task,
)
from loopora.executor_alignment_agreement_task_dispatch_types import AgreementTaskFactoryRoute

DATA_TASK_AGREEMENT_FACTORY_ROUTES: dict[str, AgreementTaskFactoryRoute] = {
    "backup_restore_recovery": (
        _agreement_is_backup_restore_recovery_task,
        (
            data_task_responses.alignment_chinese_backup_restore_recovery_agreement_response,
            data_task_responses.alignment_spanish_backup_restore_recovery_agreement_response,
            data_task_responses.alignment_english_backup_restore_recovery_agreement_response,
        ),
    ),
    "audit_log_integrity_retention": (
        _agreement_is_audit_log_integrity_retention_task,
        (
            data_task_responses.alignment_chinese_audit_log_integrity_retention_agreement_response,
            data_task_responses.alignment_spanish_audit_log_integrity_retention_agreement_response,
            data_task_responses.alignment_english_audit_log_integrity_retention_agreement_response,
        ),
    ),
    "database_schema_migration": (
        _agreement_is_database_schema_migration_task,
        (
            data_task_responses.alignment_chinese_database_schema_migration_agreement_response,
            data_task_responses.alignment_spanish_database_schema_migration_agreement_response,
            data_task_responses.alignment_english_database_schema_migration_agreement_response,
        ),
    ),
    "cdc_replication_consistency": (
        _agreement_is_cdc_replication_consistency_task,
        (
            data_task_responses.alignment_chinese_cdc_replication_consistency_agreement_response,
            data_task_responses.alignment_spanish_cdc_replication_consistency_agreement_response,
            data_task_responses.alignment_english_cdc_replication_consistency_agreement_response,
        ),
    ),
    "dsar_data_export": (
        _agreement_is_dsar_data_export_task,
        (
            data_task_responses.alignment_chinese_dsar_data_export_agreement_response,
            data_task_responses.alignment_spanish_dsar_data_export_agreement_response,
            data_task_responses.alignment_english_dsar_data_export_agreement_response,
        ),
    ),
    "data_lifecycle_deletion_retention": (
        _agreement_is_data_lifecycle_deletion_retention_task,
        (
            data_task_responses.alignment_chinese_data_lifecycle_deletion_retention_agreement_response,
            data_task_responses.alignment_spanish_data_lifecycle_deletion_retention_agreement_response,
            data_task_responses.alignment_english_data_lifecycle_deletion_retention_agreement_response,
        ),
    ),
    "data_import_validation": (
        _agreement_is_data_import_validation_task,
        (
            data_task_responses.alignment_chinese_data_import_validation_agreement_response,
            data_task_responses.alignment_spanish_data_import_validation_agreement_response,
            data_task_responses.alignment_english_data_import_validation_agreement_response,
        ),
    ),
    "file_upload_storage_safety": (
        _agreement_is_file_upload_storage_safety_task,
        (
            data_task_responses.alignment_chinese_file_upload_storage_safety_agreement_response,
            data_task_responses.alignment_spanish_file_upload_storage_safety_agreement_response,
            data_task_responses.alignment_english_file_upload_storage_safety_agreement_response,
        ),
    ),
}
