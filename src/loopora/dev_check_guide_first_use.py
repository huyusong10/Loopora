from __future__ import annotations

from loopora.dev_check_guide_types import FocusedCheckGuide


FIRST_USE_READINESS_GUIDE = FocusedCheckGuide(
    id="first_use_readiness",
    label="First-use readiness and local recovery",
    when="CLI doctor/init output, adapter setup, App/Web readiness, or development reset behavior changed.",
    command="uv run pytest -q tests/checks/contracts/test_cli_first_use_help_language.py "
    "tests/checks/contracts/test_diagnostics_redaction_contract.py "
    "tests/checks/contracts/test_cli_dev_reset.py "
    "tests/checks/contracts/test_cli_first_use_public_guidance.py "
    "tests/checks/contracts/test_cli_background_worker_runtime.py "
    "tests/checks/contracts/test_projection_first_run_fields.py "
    "tests/checks/contracts/test_public_open_source_docs.py "
    "tests/checks/contracts/test_cli_console_script_entry.py "
    "tests/checks/contracts/test_cli_run_task_verdict_output.py "
    "tests/checks/contracts/test_cli_shell_recovery.py "
    "tests/checks/contracts/test_db_schema_reset.py "
    "tests/checks/contracts/test_agent_adapter_check_entry_contracts.py "
    "tests/checks/contracts/test_agent_adapter_cli_submitted_output.py "
    "tests/checks/contracts/test_agent_adapter_compacted_01.py "
    "tests/checks/contracts/test_agent_adapter_install_cli_idempotence.py "
    "tests/checks/contracts/test_agent_adapter_install_recovery.py "
    "tests/checks/contracts/test_agent_adapter_install_safety.py "
    "tests/checks/contracts/test_agent_adapter_install_native_surface.py "
    "tests/checks/contracts/test_agent_adapter_obsolete_cleanup.py "
    "tests/checks/contracts/test_agent_adapter_service_architecture.py "
    "tests/checks/contracts/test_agent_adapter_status_drift.py "
    "tests/checks/contracts/test_agent_adapter_web_api.py "
    "tests/checks/contracts/test_cli_loop_resource_commands.py "
    "tests/checks/contracts/test_cli_loop_create_strategy_and_logs.py "
    "tests/checks/contracts/test_cli_orchestration_resource_commands.py "
    "tests/checks/contracts/test_cli_role_resource_commands.py "
    "tests/checks/contracts/test_cli_spec_prompt_commands.py "
    "tests/checks/contracts/test_cli_run_creation_options.py",
    evidence_type="focused",
    path_patterns=(
        "src/loopora/action_readiness_projection.py",
        "src/loopora/diagnose_doctor*.py",
        "src/loopora/cli_diagnose_doctor_language.py",
        "src/loopora/cli_diagnose_doctor*_output.py",
        "src/loopora/cli_diagnose_source_checkout.py",
        "src/loopora/cli_demo_commands.py",
        "src/loopora/demo_environment.py",
        "src/loopora/assets/demo/",
        "src/loopora/cli_common.py",
        "src/loopora/cli_diagnose_commands.py",
        "src/loopora/cli_recovery_commands.py",
        "src/loopora/cli_recovery_language.py",
        "src/loopora/cli_recovery_projection.py",
        "src/loopora/cli_recovery_archive_guidance.py",
        "src/loopora/recovery_archive.py",
        "src/loopora/recovery_restore.py",
        "src/loopora/cli_current_agent_setup_output.py",
        "src/loopora/cli_first_use_compact_output.py",
        "src/loopora/cli_first_task_handoff.py",
        "src/loopora/cli_group_help.py",
        "src/loopora/cli_shell_recovery.py",
        "src/loopora/cli_adapter_recovery.py",
        "src/loopora/cli_slash_recovery.py",
        "src/loopora/cli_loop*",
        "src/loopora/loop_compose_validation.py",
        "src/loopora/cli_orchestration*.py",
        "src/loopora/cli_options.py",
        "src/loopora/cli_prompt_commands.py",
        "src/loopora/cli_resource_projection.py",
        "src/loopora/cli_resource_recovery.py",
        "src/loopora/cli_role*.py",
        "src/loopora/cli_root_commands.py",
        "src/loopora/cli_status_commands.py",
        "src/loopora/existing_work_status.py",
        "src/loopora/cli_serve_command_projection.py",
        "src/loopora/cli_serve_commands.py",
        "src/loopora/cli_serve_language.py",
        "src/loopora/cli_serve_output.py",
        "src/loopora/cli_serve_recovery.py",
        "src/loopora/cli_serve_recovery_projection.py",
        "src/loopora/cli_serve_terminal.py",
        "src/loopora/cli_serve_workdir_recovery.py",
        "src/loopora/cli_start_commands.py",
        "src/loopora/cli_support_output.py",
        "src/loopora/cli_fit_commands.py",
        "src/loopora/cli_fit_output.py",
        "src/loopora/cli_fit_output_common.py",
        "src/loopora/cli_fit_review_output.py",
        "src/loopora/cli_fit_route_output.py",
        "src/loopora/cli_run_commands.py",
        "src/loopora/cli_run_output.py",
        "src/loopora/cli_shared.py",
        "src/loopora/cli_spec*.py",
        "src/loopora/cli_agent_runtime_commands.py",
        "src/loopora/cli_agent_adapter*",
        "src/loopora/cli.py",
        "src/loopora/app_state_readiness.py",
        "src/loopora/first_use_action_readiness.py",
        "src/loopora/first_use_review_actions.py",
        "src/loopora/first_use_route_projection.py",
        "src/loopora/first_use_route_terminal.py",
        "src/loopora/first_use_web_guidance.py",
        "src/loopora/first_use_route_readiness.py",
        "src/loopora/first_use_same_agent_setup.py",
        "src/loopora/first_use_web_recovery.py",
        "src/loopora/local_web_service.py",
        "src/loopora/web_service_probe.py",
        "src/loopora/agent_web.py",
        "src/loopora/fit_guidance*.py",
        "src/loopora/fit_review_catalog.py",
        "src/loopora/fit_review_completion_commands.py",
        "src/loopora/fit_review_first_task_messages.py",
        "src/loopora/fit_review_guidance.py",
        "src/loopora/start_guidance.py",
        "src/loopora/start_guidance_action_output.py",
        "src/loopora/start_guidance_actions.py",
        "src/loopora/start_guidance_constants.py",
        "src/loopora/start_guidance_next_actions.py",
        "src/loopora/start_guidance_output.py",
        "src/loopora/start_guidance_route_output.py",
        "src/loopora/start_guidance_projection.py",
        "src/loopora/serve_browser_open.py",
        "src/loopora/support_guidance*.py",
        "src/loopora/support_issue_bundle.py",
        "src/loopora/agent_adapter*",
        "src/loopora/db_schema*",
        "src/loopora/dev_reset.py",
        "src/loopora/cli_dev_reset_output.py",
        "src/loopora/service_agent_adapters.py",
        "src/loopora/service_loop_create_inputs.py",
        "src/loopora/static/pages/tools.js",
        "src/loopora/spec_recovery_commands.py",
        "src/loopora/specs.py",
        "src/loopora/workdir_inputs.py",
        "src/loopora/web_route_diagnostics_api.py",
        "src/loopora/web_route_agent_adapters_api.py",
        "src/loopora/web_route_context_help_pages.py",
        "tests/checks/contracts/test_cli_console_script_entry.py",
        "tests/checks/contracts/test_cli_background_worker_runtime.py",
        "tests/checks/contracts/test_cli_first_use*",
        "tests/checks/contracts/test_projection_first_run_fields.py",
        "tests/checks/contracts/cli_first_use*",
        "tests/checks/contracts/cli_diagnose_redaction_test_support.py",
        "tests/checks/contracts/cli_shell_recovery_test_support.py",
        "tests/checks/contracts/test_readme_first_use_commands.py",
        "tests/checks/contracts/test_cli_shell_recovery.py",
        "tests/checks/contracts/test_cli_loop_resource_commands.py",
        "tests/checks/contracts/cli_loop_resource_command_test_support.py",
        "tests/checks/contracts/test_cli_loop_create_strategy_and_logs.py",
        "tests/checks/contracts/test_cli_orchestration_resource_commands.py",
        "tests/checks/contracts/test_cli_role_resource_commands.py",
        "tests/checks/contracts/test_cli_spec_prompt_commands.py",
        "tests/checks/contracts/test_cli_run_creation_options.py",
        "tests/checks/contracts/test_db_schema_reset.py",
        "tests/checks/contracts/app_state_recovery_test_support.py",
        "tests/checks/contracts/test_agent_adapter*",
        "tests/checks/contracts/agent_adapter*",
        "tests/checks/contracts/test_web_local_asset_diagnostics.py",
        "tests/conftest.py",
    ),
)


__all__ = ("FIRST_USE_READINESS_GUIDE",)
