from __future__ import annotations

from loopora.service_runner_step_artifacts import RunnerStepResultEntryRequest, ServiceRunnerStepArtifactsMixin
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_runner_step_artifacts import RunnerStepWriteRequest


def test_runner_step_result_entry_records_step_instruction_context_without_legacy_mirror() -> None:
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
    assert "context_packet" not in entry


def test_runner_step_artifact_write_rejects_bool_identity(tmp_path) -> None:
    layout = RunArtifactLayout(tmp_path / "run")
    layout.initialize()
    service = _RunnerStepArtifactsHarness()
    bool_iter_id = True
    bool_step_order = True

    result = service.write_runner_step_result_artifacts(
        RunnerStepWriteRequest(
            run_id="run_bool_identity",
            layout=layout,
            iter_id=bool_iter_id,
            step={"id": "builder_step"},
            step_order=bool_step_order,
            role={"id": "builder", "name": "Builder", "archetype": "builder"},
            runtime_role="builder",
            normalized_output={"summary": "Built the slice.", "changed_files": []},
        )
    )

    assert result.evidence_entry["id"] == "ev_000_00_builder_step"
    assert service.step_outputs[0]["iter_id"] == 0
    assert service.step_outputs[0]["step_order"] == 0
    assert service.events[0][2]["iter"] == 0
    assert service.events[0][2]["step_order"] == 0
    assert service.events[0][2]["handoff_path"] == "iterations/iter_000/steps/00__builder_step/handoff.json"


class _RunnerStepArtifactsHarness(ServiceRunnerStepArtifactsMixin):
    def __init__(self) -> None:
        self.events = []
        self.step_outputs = []

    def _write_step_outputs(self, request) -> None:
        self.step_outputs.append({"iter_id": request.iter_id, "step_order": request.step_order})

    def append_run_event(self, *args, **_kwargs) -> None:
        self.events.append(args)
