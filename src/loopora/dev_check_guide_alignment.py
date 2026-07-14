from __future__ import annotations

from loopora.dev_check_guide_types import FocusedCheckGuide


ALIGNMENT_BUNDLE_GUIDE = FocusedCheckGuide(
    id="alignment_bundle",
    label="Alignment and bundle compiler behavior",
    when="Alignment dialogue, bundle candidates, READY validation, traceability, or domain workflow routing changed.",
    command="uv run pytest -q tests/checks/contracts/test_alignment_bundle_compacted_01.py "
    "tests/checks/contracts/test_agent_bundle_compacted_01.py "
    "tests/checks/contracts/test_alignment_confirmed_agreement_traceability_service.py "
    "tests/checks/contracts/test_alignment_import.py "
    "tests/checks/contracts/test_alignment_session_api_bundle_lifecycle.py "
    "tests/checks/contracts/test_agent_entry_review_projection.py "
    "tests/checks/contracts/test_asset_catalog_compacted_01.py "
    "tests/checks/contracts/test_bundle_delete_preflight_guards.py "
    "tests/checks/contracts/test_cli_bundle_delete_command.py "
    "tests/checks/contracts/test_cli_bundle_export_command.py "
    "tests/checks/contracts/test_cli_bundle_import_command.py "
    "tests/checks/contracts/test_strategy_source.py "
    "tests/checks/contracts/test_strategy_source_asset_architecture.py "
    "tests/checks/contracts/test_strategy_source_compacted_01.py "
    "tests/checks/contracts/test_strategy_source_definitions_export_ownership.py "
    "tests/checks/contracts/test_strategy_source_facade_helper_ownership.py "
    "tests/checks/contracts/test_strategy_source_legacy_definition_ownership.py "
    "tests/checks/contracts/test_strategy_source_runtime_architecture.py "
    "tests/checks/contracts/test_strategy_source_web_architecture.py "
    "tests/checks/contracts/test_workflow_file_loading.py",
    evidence_type="focused",
    path_patterns=(
        "src/loopora/action_readiness_projection.py",
        "src/loopora/alignment*",
        "src/loopora/asset_catalog*",
        "src/loopora/asset_errors.py",
        "src/loopora/bundle*",
        "src/loopora/cli_bundle*.py",
        "src/loopora/cli_resource_projection.py",
        "src/loopora/cli_resource_recovery.py",
        "src/loopora/compiler/",
        "src/loopora/db_alignment_records.py",
        "src/loopora/db_bundle_graph_records.py",
        "src/loopora/db_bundle_records.py",
        "src/loopora/existing_work_status.py",
        "src/loopora/service_orchestration_assets.py",
        "src/loopora/service_role_definition_assets.py",
        "src/loopora/service_agent_bundle_candidate*.py",
        "src/loopora/service_agent_bundle_candidates.py",
        "src/loopora/service_bundle*",
        "src/loopora/service_alignment*",
        "src/loopora/assets/alignment/",
        "src/loopora/assets/system_prompts/alignment/",
        "src/loopora/strategy_source*",
        "src/loopora/web_home_attention.py",
        "tests/checks/contracts/test_alignment*",
        "tests/checks/contracts/alignment*",
        "tests/checks/contracts/agent_bundle*",
        "tests/checks/contracts/test_agent_bundle*",
        "tests/checks/contracts/test_agent_entry*",
        "tests/checks/contracts/test_asset_catalog*",
        "tests/checks/contracts/test_bundle*",
        "tests/checks/contracts/test_task_role_governance_asset_contract.py",
        "tests/checks/contracts/test_cli_bundle_delete_command.py",
        "tests/checks/contracts/test_cli_bundle_export_command.py",
        "tests/checks/contracts/test_cli_bundle_import_command.py",
        "tests/checks/contracts/test_strategy_source*",
        "tests/checks/contracts/cli_bundle*",
        "tests/checks/contracts/test_workflow_file_loading.py",
        "tests/checks/contracts/bundle*",
    ),
)


__all__ = ("ALIGNMENT_BUNDLE_GUIDE",)
