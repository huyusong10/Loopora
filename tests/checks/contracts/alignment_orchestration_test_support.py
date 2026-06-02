import logging

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


def execute_alignment_orchestration(harness: AlignmentOrchestrationHarness) -> None:
    execute_alignment_session(
        harness.context(),
        "align_1",
        logger=logging.getLogger("tests.alignment.orchestration"),
    )


__all__ = [
    "AlignmentOrchestrationHarness",
    "execute_alignment_orchestration",
]
