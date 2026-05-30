import logging

from loopora.executor import ExecutionStopped
from loopora.service_alignment_execution import AlignmentExecutionState
from loopora.service_alignment_orchestration import AlignmentSessionOrchestrationContext, execute_alignment_session
from loopora.service_alignment_session_lifecycle import alignment_thread_key


class FakeAlignmentOrchestrationRepository:
    def __init__(self) -> None:
        self.updates: list[dict] = []

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        self.updates.append({"session_id": session_id, "fields": fields})
        return {"id": session_id, **fields}


class FakeAlignmentOrchestrationThread:
    def __init__(self, *, alive: bool = False) -> None:
        self.alive = alive

    def is_alive(self) -> bool:
        return self.alive


class AlignmentOrchestrationHarness:
    def __init__(self, outputs: list[dict]) -> None:
        self.repository = FakeAlignmentOrchestrationRepository()
        self.outputs = list(outputs)
        self.run_requests: list[dict] = []
        self.stage_applications: list[dict] = []
        self.projected_outputs: list[dict] = []
        self.recorded_messages: list[dict] = []
        self.bundle_candidates: list[str] = []
        self.bundle_candidate_states: list[AlignmentExecutionState | None] = []
        self.transition_actions: list[str] = []
        self.failures: list[dict] = []
        self.threads: dict[str, FakeAlignmentOrchestrationThread] = {
            "alignment:align_1": FakeAlignmentOrchestrationThread(alive=False),
        }

    def get_session(self, session_id: str) -> dict:
        return {"id": session_id, "status": "running"}

    def run_executor(self, session_id: str, *, mode: str, validation_error: str = "", invalid_yaml: str = "") -> dict:
        self.run_requests.append(
            {
                "session_id": session_id,
                "mode": mode,
                "validation_error": validation_error,
                "invalid_yaml": invalid_yaml,
            }
        )
        output = self.outputs.pop(0)
        if isinstance(output.get("raise"), BaseException):
            raise output["raise"]
        return output

    def apply_output_stage(self, session_id: str, session: dict, output: dict) -> dict:
        self.stage_applications.append({"session_id": session_id, "output": output})
        return {**session, "alignment_stage": str(output.get("alignment_phase", "") or "clarifying")}

    def output_message_bundle_and_options(self, session_id: str, session: dict, output: dict):
        self.projected_outputs.append({"session_id": session_id, "session": session, "output": output})
        return (
            str(output.get("assistant_message", "") or ""),
            str(output.get("bundle_yaml", "") or "").strip(),
            list(output.get("decision_options") or []),
            output.get("missing_items"),
        )

    def record_assistant_message(
        self,
        session_id: str,
        session: dict,
        assistant_message: str,
        *,
        decision_options: list[dict] | None = None,
        missing_items: list[str] | None = None,
    ) -> None:
        self.recorded_messages.append(
            {
                "session_id": session_id,
                "session": session,
                "message": assistant_message,
                "decision_options": decision_options,
                "missing_items": missing_items,
            }
        )

    def handle_bundle_candidate(self, _session_id: str, bundle_yaml: str) -> AlignmentExecutionState | None:
        self.bundle_candidates.append(bundle_yaml)
        return self.bundle_candidate_states.pop(0) if self.bundle_candidate_states else None

    def apply_transition_plan(self, _session_id: str, plan) -> None:
        self.transition_actions.append(plan.action)

    def fail_session(self, session_id: str, error: str, *, event_type: str = "alignment_failed") -> None:
        self.failures.append({"session_id": session_id, "error": error, "event_type": event_type})

    def context(self) -> AlignmentSessionOrchestrationContext:
        return AlignmentSessionOrchestrationContext(
            repository=self.repository,
            get_session=self.get_session,
            run_executor=self.run_executor,
            apply_output_stage=self.apply_output_stage,
            output_message_bundle_and_options=self.output_message_bundle_and_options,
            record_assistant_message=self.record_assistant_message,
            handle_bundle_candidate=self.handle_bundle_candidate,
            apply_transition_plan=self.apply_transition_plan,
            fail_session=self.fail_session,
            threads=self.threads,
            thread_key=alignment_thread_key,
        )


def test_alignment_orchestration_accepts_bundle_candidate_and_cleans_dead_worker_thread() -> None:
    harness = AlignmentOrchestrationHarness(
        [
            {
                "alignment_phase": "bundle",
                "assistant_message": "I prepared the Loop.",
                "bundle_yaml": "version: 1\n",
                "decision_options": [{"id": "import"}],
                "missing_items": ["runtime_contract"],
            }
        ]
    )

    execute_alignment_session(harness.context(), "align_1", logger=logging.getLogger("tests.alignment.orchestration"))

    assert harness.run_requests == [
        {"session_id": "align_1", "mode": "normal", "validation_error": "", "invalid_yaml": ""}
    ]
    assert harness.recorded_messages[0]["message"] == "I prepared the Loop."
    assert harness.recorded_messages[0]["decision_options"] == [{"id": "import"}]
    assert harness.recorded_messages[0]["missing_items"] == ["runtime_contract"]
    assert harness.bundle_candidates == ["version: 1"]
    assert harness.failures == []
    assert harness.repository.updates[-1] == {"session_id": "align_1", "fields": {"clear_active_child_pid": True}}
    assert "alignment:align_1" not in harness.threads


def test_alignment_orchestration_reenters_executor_with_repair_state_before_ready() -> None:
    harness = AlignmentOrchestrationHarness(
        [
            {"alignment_phase": "bundle", "assistant_message": "First draft.", "bundle_yaml": "bad: yaml"},
            {"alignment_phase": "bundle", "assistant_message": "Repaired draft.", "bundle_yaml": "version: 1\n"},
        ]
    )
    harness.bundle_candidate_states = [
        AlignmentExecutionState(mode="repair", validation_error="missing evidence flow", invalid_yaml="bad: yaml"),
        None,
    ]

    execute_alignment_session(harness.context(), "align_1", logger=logging.getLogger("tests.alignment.orchestration"))

    assert harness.run_requests == [
        {"session_id": "align_1", "mode": "normal", "validation_error": "", "invalid_yaml": ""},
        {
            "session_id": "align_1",
            "mode": "repair",
            "validation_error": "missing evidence flow",
            "invalid_yaml": "bad: yaml",
        },
    ]
    assert harness.bundle_candidates == ["bad: yaml", "version: 1"]
    assert [item["message"] for item in harness.recorded_messages] == ["First draft.", "Repaired draft."]


def test_alignment_orchestration_waits_for_user_without_promoting_runtime_success_to_bundle() -> None:
    harness = AlignmentOrchestrationHarness(
        [{"needs_user_input": True, "assistant_message": "I need one decision before compiling."}]
    )

    execute_alignment_session(harness.context(), "align_1", logger=logging.getLogger("tests.alignment.orchestration"))

    assert harness.transition_actions == ["waiting_user"]
    assert harness.bundle_candidates == []
    assert harness.failures == []


def test_alignment_orchestration_records_cancelled_execution_as_cancelled_failure() -> None:
    harness = AlignmentOrchestrationHarness([{"raise": ExecutionStopped("stop requested")}])

    execute_alignment_session(harness.context(), "align_1", logger=logging.getLogger("tests.alignment.orchestration"))

    assert harness.failures == [
        {"session_id": "align_1", "error": "Cancelled by user.", "event_type": "alignment_cancelled"}
    ]
    assert harness.repository.updates[-1] == {"session_id": "align_1", "fields": {"clear_active_child_pid": True}}
