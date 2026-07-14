from __future__ import annotations

from loopora.dev_check_guide_types import FocusedCheckGuide


CORE_EXECUTION_GUIDE = FocusedCheckGuide(
    id="core_execution",
    label="Core execution, context, and provider boundaries",
    when="Kernel/Event Core, RunEngine events, StepInstruction context, executor, or provider profile boundaries changed.",
    command="uv run pytest -q tests/checks/contracts/kernel "
    "tests/checks/contracts/test_context_schema_architecture.py "
    "tests/checks/contracts/test_context_schema_prompt_architecture.py "
    "tests/checks/contracts/test_executor_facade_architecture.py "
    "tests/checks/contracts/test_executor_command_validation_architecture.py "
    "tests/checks/contracts/test_executor_command_args.py "
    "tests/checks/contracts/test_executor_command_events.py "
    "tests/checks/contracts/test_executor_alignment_fixture_architecture.py "
    "tests/checks/contracts/test_executor_codex_output_contract.py "
    "tests/checks/contracts/test_executor_process_stream.py "
    "tests/checks/contracts/test_executor_session_refs.py "
    "tests/checks/contracts/test_real_executor_architecture.py "
    "tests/checks/contracts/test_provider_profile_catalog.py "
    "tests/checks/contracts/test_provider_normalization.py",
    evidence_type="focused",
    path_patterns=(
        "src/loopora/context*",
        "src/loopora/engine/",
        "src/loopora/events/",
        "src/loopora/executor*",
        "src/loopora/kernel/",
        "src/loopora/provider*",
        "tests/checks/contracts/context_architecture_test_support.py",
        "tests/checks/contracts/executor*",
        "tests/checks/contracts/kernel/",
        "tests/checks/contracts/test_context_schema*",
        "tests/checks/contracts/test_executor*",
        "tests/checks/contracts/test_real_executor_architecture.py",
        "tests/checks/contracts/test_provider*",
    ),
)


__all__ = ("CORE_EXECUTION_GUIDE",)
