from __future__ import annotations

from loopora.executor_alignment_bundle_task_predicates import (
    _is_audit_log_integrity_retention_task,
    _is_backup_restore_recovery_task,
    _is_cache_invalidation_consistency_task,
    _is_cdc_replication_consistency_task,
    _is_data_import_validation_task,
    _is_data_lifecycle_deletion_retention_task,
    _is_database_schema_migration_task,
    _is_dsar_data_export_task,
    _is_file_upload_storage_safety_task,
)
from loopora.executor_alignment_bundle_task_spec_notes import (
    append_task_spec_workflow_note_for_task as _append_note,
    task_spec_workflow_note_context as _note_context,
)


def _append_backup_restore_recovery_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_backup_restore_recovery_task,
        "backup_restore_recovery",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_audit_log_integrity_retention_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_audit_log_integrity_retention_task,
        "audit_log_integrity_retention",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_database_schema_migration_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_database_schema_migration_task,
        "database_schema_migration",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_cdc_replication_consistency_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_cdc_replication_consistency_task,
        "cdc_replication_consistency",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_data_lifecycle_deletion_retention_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_data_lifecycle_deletion_retention_task,
        "data_lifecycle_deletion_retention",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_cache_invalidation_consistency_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_cache_invalidation_consistency_task,
        "cache_invalidation_consistency",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_data_import_validation_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_data_import_validation_task,
        "data_import_validation",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_dsar_data_export_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_dsar_data_export_task,
        "dsar_data_export",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )


def _append_file_upload_storage_safety_spec_notes(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    _append_note(
        bundle,
        _is_file_upload_storage_safety_task,
        "file_upload_storage_safety",
        _note_context(prefers_chinese=prefers_chinese, task=task, display_language=display_language),
    )
