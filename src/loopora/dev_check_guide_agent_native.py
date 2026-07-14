from __future__ import annotations

from loopora.dev_check_guide_types import FocusedCheckGuide


AGENT_NATIVE_GUIDE = FocusedCheckGuide(
    id="agent_native",
    label="Agent Native plan/run surfaces",
    when="Managed /loopora-plan or /loopora-run guidance, compact Agent output, recovery, or submit behavior changed.",
    command="uv run pytest -q tests/checks/contracts/test_agent_native_compacted_01.py "
    "tests/checks/contracts/test_cli_agent_compacted_01.py "
    "tests/checks/contracts/test_agent_native_cli_run_surface.py "
    "tests/checks/contracts/test_agent_adapter_web_api.py "
    "tests/checks/contracts/test_cli_recoverable_context_preview_choices.py "
    "tests/checks/contracts/test_cli_recoverable_context_terminal_choices.py "
    "tests/checks/contracts/test_agent_run_context_choice_payloads.py "
    "tests/checks/contracts/test_agent_run_context_choice_recovery_projection.py "
    "tests/checks/contracts/test_agent_next_dispatch_recovery_commands.py "
    "tests/checks/contracts/test_agent_context_binding_scope.py "
    "tests/checks/contracts/test_agent_cli_step_dispatch_output.py "
    "tests/checks/contracts/test_system_prompt_asset_ownership.py "
    "tests/checks/contracts/test_agent_work_panel_task_proof.py",
    evidence_type="focused",
    path_patterns=(
        "src/loopora/agent_native*",
        "src/loopora/agent_entry*",
        "src/loopora/agent_web.py",
        "src/loopora/cli_agent*",
        "src/loopora/cli_first_task_handoff.py",
        "src/loopora/service_agent_bundle_candidate*.py",
        "src/loopora/service_agent_bundle_candidates.py",
        "src/loopora/service_agent_continuation.py",
        "src/loopora/service_agent_entry_projection.py",
        "src/loopora/service_agent_loop_start.py",
        "src/loopora/service_agent_loop_start_bindings.py",
        "src/loopora/service_agent_native.py",
        "src/loopora/service_agent_adapters.py",
        "src/loopora/service_agent_run_context_binding.py",
        "src/loopora/assets/system_prompts/agent_native/",
        "tests/checks/contracts/test_agent_native*",
        "tests/checks/contracts/test_agent_adapter_web_api.py",
        "tests/checks/contracts/agent_native*",
        "tests/checks/contracts/test_cli_agent*",
        "tests/checks/contracts/cli_agent*",
        "tests/checks/contracts/test_cli_recoverable_context*",
        "tests/checks/contracts/test_agent_loop*",
        "tests/checks/contracts/test_agent_plan*",
        "tests/checks/contracts/test_agent_next*",
        "tests/checks/contracts/test_agent_cli*",
        "tests/checks/contracts/test_agent_run_context_choice*",
        "tests/checks/contracts/test_agent_context_binding_scope.py",
        "tests/checks/contracts/test_system_prompt_asset_ownership.py",
        "tests/checks/contracts/test_agent_work_panel_task_proof.py",
        "tests/checks/contracts/compacted_agent_native*",
    ),
)


__all__ = ("AGENT_NATIVE_GUIDE",)
