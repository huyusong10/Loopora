from __future__ import annotations

from loopora.dev_check_guide_types import FocusedCheckGuide


RUNTIME_STATE_GUIDE = FocusedCheckGuide(
    id="runtime_state",
    label="Run lifecycle and local runtime state",
    when="Run lifecycle, run observation, Loop deletion, workspace guards, settings, or local App state changed.",
    command="uv run pytest -q tests/checks/contracts/test_runner_acceptance_architecture.py "
    "tests/checks/contracts/test_runner_recovery_architecture.py "
    "tests/checks/contracts/test_runner_run_registration_cleanup.py "
    "tests/checks/contracts/test_runner_run_engine_integration_architecture.py "
    "tests/checks/contracts/test_runner_inspect_first_workflow_preset.py "
    "tests/checks/contracts/test_runner_local_execution.py "
    "tests/checks/contracts/test_runner_stop_lifecycle.py "
    "tests/checks/contracts/test_runner_triage_fast_lane_workflow_presets.py "
    "tests/checks/contracts/test_run_lifecycle_projection_architecture.py "
    "tests/checks/contracts/test_run_takeaway_projection_architecture.py "
    "tests/checks/contracts/test_loop_deletion_cleanup.py "
    "tests/checks/contracts/test_cleanup_diagnostics.py "
    "tests/checks/contracts/test_api_file_preview_read_errors.py "
    "tests/checks/contracts/test_web_local_asset_diagnostics.py "
    "tests/checks/contracts/test_cli_diagnose_event_redaction_fix.py "
    "tests/checks/contracts/test_cli_diagnose_event_redaction_orphans.py "
    "tests/checks/contracts/test_diagnostics_redaction_contract.py "
    "tests/checks/contracts/test_event_redaction_architecture.py "
    "tests/checks/contracts/test_event_redaction_audit_architecture.py "
    "tests/checks/contracts/test_cli_background_worker_runtime.py "
    "tests/checks/contracts/test_cli_run_task_verdict_output.py "
    "tests/checks/contracts/test_db_run_constraints.py "
    "tests/checks/contracts/test_run_file_access_service_boundary.py "
    "tests/checks/contracts/test_run_artifact_download_path_escape.py "
    "tests/checks/contracts/test_run_artifacts.py "
    "tests/checks/contracts/test_run_contract_snapshot_strategy_source_architecture.py "
    "tests/checks/contracts/test_runner_agent_native_runtime_architecture.py "
    "tests/checks/contracts/test_runner_evidence_boundary_architecture.py "
    "tests/checks/contracts/test_runner_failure_lifecycle.py "
    "tests/checks/contracts/test_runner_prompt_artifact_recovery.py "
    "tests/checks/contracts/test_runner_role_runtime_architecture.py "
    "tests/checks/contracts/test_runner_runtime_number_contracts.py "
    "tests/checks/contracts/test_runner_workspace_guard.py "
    "tests/checks/contracts/test_service_asset_call_errors.py "
    "tests/checks/contracts/test_service_component_boundaries.py "
    "tests/checks/contracts/test_service_composition_facade.py "
    "tests/checks/contracts/test_service_orchestration_assets.py "
    "tests/checks/contracts/test_service_private_import_inventory.py "
    "tests/checks/contracts/test_service_prompt_schema_architecture.py "
    "tests/checks/contracts/test_settings_architecture.py "
    "tests/checks/contracts/test_settings_payload_normalization.py "
    "tests/checks/contracts/test_settings_paths.py "
    "tests/checks/contracts/test_settings_recent_workdirs.py",
    evidence_type="focused",
    path_patterns=(
        "src/loopora/action_readiness_projection.py",
        "src/loopora/app_state_readiness.py",
        "src/loopora/branding.py",
        "src/loopora/cli_loop_create_flow.py",
        "src/loopora/cli_loop_commands.py",
        "src/loopora/cli_loop_export_commands.py",
        "src/loopora/cli_loop_saved_work.py",
        "src/loopora/cli_run_commands.py",
        "src/loopora/cli_run_output.py",
        "src/loopora/cli_run_support.py",
        "src/loopora/cli_recovery_archive_guidance.py",
        "src/loopora/cli_status_commands.py",
        "src/loopora/db.py",
        "src/loopora/db_local_asset_records.py",
        "src/loopora/db_run_records.py",
        "src/loopora/db_run_slots.py",
        "src/loopora/event_redaction*.py",
        "src/loopora/existing_work_status.py",
        "src/loopora/local_workdir_artifacts.py",
        "src/loopora/loop_run_progress.py",
        "src/loopora/runner_role_execution_settings.py",
        "src/loopora/run_observation_events.py",
        "src/loopora/run_continuation_progress.py",
        "src/loopora/run_evidence_package.py",
        "src/loopora/run_result_recording.py",
        "src/loopora/run_worker_start.py",
        "src/loopora/service.py",
        "src/loopora/service_app.py",
        "src/loopora/service_cleanup_diagnostics.py",
        "src/loopora/service_local_asset_*.py",
        "src/loopora/service_loop_deletion.py",
        "src/loopora/service_loop_records.py",
        "src/loopora/service_loop_prompt_files.py",
        "src/loopora/service_prompt*",
        "src/loopora/service_prompts.py",
        "src/loopora/service_run_*.py",
        "src/loopora/service_runner_failure_handling.py",
        "src/loopora/service_types.py",
        "src/loopora/service_workspace.py",
        "src/loopora/settings*",
        "src/loopora/utils.py",
        "src/loopora/web_home_attention.py",
        "src/loopora/web_route*run*.py",
        "src/loopora/web_run_*.py",
        "src/loopora/web_task_verdict_overviews.py",
        "src/loopora/web_timeline*.py",
        "src/loopora/workdir_inputs.py",
        "tests/checks/contracts/runner_helpers.py",
        "tests/checks/contracts/runner_architecture_test_support.py",
        "tests/checks/contracts/service_architecture_test_support.py",
        "tests/checks/contracts/settings_*",
        "tests/checks/contracts/strategy_source_architecture_test_support.py",
        "tests/checks/contracts/test_loop_deletion_cleanup.py",
        "tests/checks/contracts/test_cleanup_diagnostics.py",
        "tests/checks/contracts/test_api_file_preview_read_errors.py",
        "tests/checks/contracts/test_cli_background_worker_runtime.py",
        "tests/checks/contracts/test_cli_diagnose_event_redaction*.py",
        "tests/checks/contracts/test_cli_run_task_verdict_output.py",
        "tests/checks/contracts/test_db_run_constraints.py",
        "tests/checks/contracts/test_diagnostics_redaction_contract.py",
        "tests/checks/contracts/test_event_redaction*.py",
        "tests/checks/contracts/test_run_artifact_download_path_escape.py",
        "tests/checks/contracts/test_run_artifacts.py",
        "tests/checks/contracts/test_run_contract_snapshot_strategy_source_architecture.py",
        "tests/checks/contracts/test_run_file_access_service_boundary.py",
        "tests/checks/contracts/test_run_lifecycle_projection_architecture.py",
        "tests/checks/contracts/test_run_takeaway_projection_architecture.py",
        "tests/checks/contracts/test_runner_agent_native_runtime_architecture.py",
        "tests/checks/contracts/test_runner_acceptance_architecture.py",
        "tests/checks/contracts/test_runner_evidence_boundary_architecture.py",
        "tests/checks/contracts/test_runner_failure_lifecycle.py",
        "tests/checks/contracts/test_runner_inspect_first_workflow_preset.py",
        "tests/checks/contracts/test_runner_local_execution.py",
        "tests/checks/contracts/test_runner_prompt_artifact_recovery.py",
        "tests/checks/contracts/test_runner_recovery_architecture.py",
        "tests/checks/contracts/test_runner_run_registration_cleanup.py",
        "tests/checks/contracts/test_runner_run_engine_integration_architecture.py",
        "tests/checks/contracts/test_runner_role_runtime_architecture.py",
        "tests/checks/contracts/test_runner_runtime_number_contracts.py",
        "tests/checks/contracts/test_runner_stop_lifecycle.py",
        "tests/checks/contracts/test_runner_triage_fast_lane_workflow_presets.py",
        "tests/checks/contracts/test_runner_workspace_guard.py",
        "tests/checks/contracts/runner_workflow_preset_test_support.py",
        "tests/checks/contracts/test_service_*.py",
        "tests/checks/contracts/test_service_prompt_schema_architecture.py",
        "tests/checks/contracts/test_settings_architecture.py",
        "tests/checks/contracts/test_settings_payload_normalization.py",
        "tests/checks/contracts/test_settings_paths.py",
        "tests/checks/contracts/test_settings_recent_workdirs.py",
        "tests/checks/contracts/test_web_local_asset_diagnostics.py",
    ),
)


__all__ = ("RUNTIME_STATE_GUIDE",)
