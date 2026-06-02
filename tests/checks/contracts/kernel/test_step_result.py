from __future__ import annotations

from loopora.engine import RunnerStepResultRequest, runner_step_result
from loopora.kernel import ActorRef, StepResultStatus


KERNEL_STEP_RESULT_ITERATION = 2


def test_runner_step_result_adapts_legacy_output_to_kernel_step_result() -> None:
    result = runner_step_result(
        RunnerStepResultRequest(
            run_id="run_123",
            iteration=KERNEL_STEP_RESULT_ITERATION,
            step={"id": "gatekeeper"},
            actor=ActorRef(kind="agent", id="codex", adapter="codex"),
            output={
                "passed": False,
                "decision_summary": "Missing permission proof.",
                "blocking_issues": ["permission proof missing"],
                "evidence_claims": ["No permission evidence is cited."],
                "coverage_results": [{"target_id": "done_when.permission", "status": "blocked"}],
                "residual_risks": ["Manual audit still needs an owner."],
            },
            handoff={
                "summary": "GateKeeper blocked closure.",
                "status": "blocked",
                "blocking_items": ["permission proof missing"],
                "artifact_refs": [
                    {"kind": "workspace", "label": "proof:report.txt", "relative_path": "report.txt"},
                ],
            },
        )
    )

    assert result.run_id == "run_123"
    assert result.step_id == "gatekeeper"
    assert result.iteration == KERNEL_STEP_RESULT_ITERATION
    assert result.status == StepResultStatus.BLOCKED
    assert result.summary == "GateKeeper blocked closure."
    assert result.blocking_items == ("permission proof missing",)
    assert result.residual_risks == ("Manual audit still needs an owner.",)
    assert result.artifact_refs[0].uri == "report.txt"
    assert result.evidence_claims[0].supports[0].target_id == "done_when.permission"
