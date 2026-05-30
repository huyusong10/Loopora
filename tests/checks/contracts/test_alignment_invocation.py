import json
from pathlib import Path

from loopora.executor import RoleRequest
from loopora.service_alignment_invocation import (
    AlignmentExecutorInvocationConfig,
    AlignmentExecutorRunContext,
    run_alignment_executor,
)


class FakeAlignmentInvocationRepository:
    def __init__(self, session: dict) -> None:
        self.session = dict(session)
        self.events: list[dict] = []
        self.updates: list[dict] = []

    def get_alignment_session(self, session_id: str) -> dict | None:
        assert session_id == self.session["id"]
        return dict(self.session)

    def update_alignment_session(self, session_id: str, **fields: object) -> dict:
        assert session_id == self.session["id"]
        self.updates.append(fields)
        if fields.pop("clear_active_child_pid", False):
            self.session.pop("active_child_pid", None)
        self.session.update(fields)
        return dict(self.session)

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict:
        assert session_id == self.session["id"]
        event = {"event_type": event_type, "payload": payload}
        self.events.append(event)
        return event

    def alignment_should_stop(self, session_id: str) -> bool:
        assert session_id == self.session["id"]
        return False


class FakeAlignmentExecutor:
    def __init__(self) -> None:
        self.requests: list[RoleRequest] = []

    def execute(self, request: RoleRequest, emit_event, should_stop, update_child_pid) -> dict:
        assert should_stop() is False
        self.requests.append(request)
        update_child_pid(4321)
        emit_event("codex_event", {"message": "executor heartbeat"})
        update_child_pid(None)
        return {
            "assistant_message": "Invocation completed.",
            "session_ref": {"session_id": "native-42", "provider": "codex"},
        }


def test_run_alignment_executor_builds_invocation_boundary_and_persists_session_ref(tmp_path: Path) -> None:
    session_id = "align_invocation"
    root = tmp_path / ".loopora" / "alignment_sessions" / session_id
    bundle_path = root / "artifacts" / "bundle.yml"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text("version: 1\n", encoding="utf-8")
    workdir = tmp_path / "project"
    workdir.mkdir()
    session = {
        "id": session_id,
        "status": "running",
        "workdir": str(workdir),
        "bundle_path": str(bundle_path),
        "alignment_stage": "confirmed",
        "executor_kind": "codex",
        "executor_mode": "preset",
        "model": "gpt-5",
        "reasoning_effort": "medium",
        "repair_attempts": 2,
    }
    repo = FakeAlignmentInvocationRepository(session)
    executor = FakeAlignmentExecutor()
    prompt_calls: list[dict] = []
    invocation_dir_calls: list[dict] = []

    def get_session(_session_id: str) -> dict:
        return dict(repo.session)

    def build_prompt(session_payload: dict, *, mode: str, validation_error: str = "", invalid_yaml: str = "") -> str:
        prompt_calls.append(
            {
                "session_id": session_payload["id"],
                "mode": mode,
                "validation_error": validation_error,
                "invalid_yaml": invalid_yaml,
            }
        )
        return "Prompt for repair."

    def next_invocation_dir(invocation_root: Path, attempt: int, *, repair: bool) -> Path:
        invocation_dir_calls.append({"root": invocation_root, "attempt": attempt, "repair": repair})
        return invocation_root / "invocations" / "repair-0002"

    context = AlignmentExecutorRunContext(
        repository=repo,
        get_session=get_session,
        config=AlignmentExecutorInvocationConfig(
            output_schema={"type": "object", "properties": {"assistant_message": {"type": "string"}}},
            idle_timeout_seconds=9.5,
            executor_factory=lambda: executor,
            build_prompt=build_prompt,
            ensure_artifact_dirs=lambda path: path.mkdir(parents=True, exist_ok=True),
            next_invocation_dir=next_invocation_dir,
            repair_attempts=lambda session_payload, *, invalid_default=0: int(session_payload.get("repair_attempts") or invalid_default),
        ),
    )

    output = run_alignment_executor(
        context,
        session_id,
        mode="repair",
        validation_error="missing evidence flow",
        invalid_yaml="bad: yaml",
    )

    invocation_dir = root / "invocations" / "repair-0002"
    assert output["assistant_message"] == "Invocation completed."
    assert prompt_calls == [
        {
            "session_id": session_id,
            "mode": "repair",
            "validation_error": "missing evidence flow",
            "invalid_yaml": "bad: yaml",
        }
    ]
    assert invocation_dir_calls == [{"root": root, "attempt": 2, "repair": True}]
    assert (invocation_dir / "prompt.md").read_text(encoding="utf-8") == "Prompt for repair.\n"
    assert json.loads((invocation_dir / "schema.json").read_text(encoding="utf-8"))["type"] == "object"
    assert "executor heartbeat" in (invocation_dir / "stdout.log").read_text(encoding="utf-8")
    output_debug = json.loads((invocation_dir / "output.json").read_text(encoding="utf-8"))
    assert output_debug["assistant_message"] == "Invocation completed."
    assert output_debug["bundle_written"] is False
    assert executor.requests[0].idle_timeout_seconds == 9.5
    assert executor.requests[0].extra_context["validation_error"] == "missing evidence flow"
    assert repo.updates[-1] == {"executor_session_ref": {"session_id": "native-42", "provider": "codex"}}
    assert [event["event_type"] for event in repo.events] == [
        "codex_event",
        "alignment_executor_session_ref",
    ]
    assert repo.events[0]["payload"]["alignment_status"] == "running"
    assert repo.events[0]["payload"]["invocation_id"] == "repair-0002"
