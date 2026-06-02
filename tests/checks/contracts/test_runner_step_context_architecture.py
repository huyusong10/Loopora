from __future__ import annotations

from runner_architecture_test_support import design_contracts_source, loopora_source


def test_runner_step_context_inputs_have_dedicated_boundary() -> None:
    runtime_source = loopora_source("service_runner_step_runtime.py")
    instruction_context_source = loopora_source("runner_step_instruction_contexts.py")
    context_inputs_source = loopora_source("runner_step_context_inputs.py")
    contracts_source = design_contracts_source()

    assert "from loopora.runner_step_instruction_contexts import prepare_runner_step_instruction_context" in runtime_source
    assert "from loopora.runner_step_context_inputs import" in instruction_context_source
    assert "def prepare_runner_step_instruction_context" in instruction_context_source
    assert "write_json(context_path, step_instruction_context)" in instruction_context_source
    assert "write_json(context_path, step_instruction_context)" not in runtime_source
    for marker in (
        "def filter_handoffs_for_step",
        "def iteration_memory_for_step",
        "def filter_evidence_for_step",
        "def merge_coverage_gap_evidence",
        "def manifest_prompt_context",
    ):
        assert marker in context_inputs_source
        assert marker not in runtime_source
    assert "runner_step_context_inputs.py" in contracts_source
    assert "runner_step_instruction_contexts.py" in contracts_source


def test_step_instruction_context_normalizers_have_dedicated_boundary() -> None:
    context_source = loopora_source("context_flow.py")
    normalizers_source = loopora_source("context_step_instruction_normalizers.py")
    contracts_source = design_contracts_source()

    assert "from loopora.context_step_instruction_normalizers import" in context_source
    for marker in (
        "def normalize_continuation_context",
        "def normalize_evidence_coverage_summary",
        "def normalize_manifest_claims",
    ):
        assert marker in normalizers_source
        assert marker not in context_source
    assert "def build_step_instruction_context" in context_source
    assert "def build_step_instruction_context" not in normalizers_source
    assert "context_step_instruction_normalizers.py" in contracts_source
