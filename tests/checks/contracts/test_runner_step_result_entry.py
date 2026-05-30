from __future__ import annotations

from loopora.service_runner_step_artifacts import RunnerStepResultEntryRequest, ServiceRunnerStepArtifactsMixin


def test_runner_step_result_entry_records_step_instruction_context_with_legacy_mirror() -> None:
    step_context = {
        "iteration": {"iter_index": 1},
        "current_step": {"step_id": "builder_step"},
        "evidence": {"known_ids": ["ev_000_00_builder_step"]},
    }

    entry = ServiceRunnerStepArtifactsMixin()._build_runner_step_result_entry(
        RunnerStepResultEntryRequest(
            step={"id": "builder_step"},
            step_order=0,
            role={"id": "builder", "name": "Builder"},
            runtime_role="builder",
            execution_settings={"model": "gpt-test", "executor_kind": "fake"},
            normalized_output={"summary": "done"},
            handoff={"status": "completed"},
            step_instruction_context=step_context,
        )
    )

    assert entry["step_instruction_context"] == step_context
    assert entry["context_packet"] == step_context
