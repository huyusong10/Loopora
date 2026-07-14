from __future__ import annotations

from agent_run_recovery_test_support import AgentRecoveryRepository
from loopora.agent_entry_continuation import agent_native_continuation_context_for_terminal_run
from loopora.run_artifacts import RunArtifactLayout
from loopora.service_alignment_run_recovery import (
    agent_run_context_choice_from_session,
    agent_run_context_choices,
)
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service_types import LooporaError


def test_agent_run_context_choice_from_session_reads_linked_run_task_verdict(tmp_path) -> None:
    repo = AgentRecoveryRepository(sessions=[], events_by_session={})
    session = {
        "id": "align_passed",
        "status": "ready",
        "workdir": str(tmp_path),
        "linked_run_id": "run_passed",
        "transcript": [{"role": "user", "content": "Ship the focused starter experience."}],
    }

    choice = agent_run_context_choice_from_session(
        repo,
        session,
        adapter="codex",
        get_run=lambda run_id: {
            "id": run_id,
            "status": "succeeded",
            "task_verdict": {"status": "passed", "summary": "Proof is sufficient."},
        },
    )

    assert choice["action"] == "replay_terminal_pass"
    assert choice["choice_status"] == "terminal_passed"
    assert choice["linked_run_status"] == "succeeded"
    assert choice["task_verdict_status"] == "passed"
    assert choice["task_verdict_summary"] == "Proof is sufficient."
    assert choice["label_en"].startswith("Replay terminal run: Ship the focused starter experience.")


def test_agent_run_context_choice_from_session_maps_lifecycle_failure_to_retry(tmp_path) -> None:
    repo = AgentRecoveryRepository(sessions=[], events_by_session={})
    session = {
        "id": "align_retry",
        "status": "running_loop",
        "workdir": str(tmp_path),
        "linked_run_id": "run_failed_start",
        "transcript": [{"role": "user", "content": "Ship the focused starter experience."}],
    }

    choice = agent_run_context_choice_from_session(
        repo,
        session,
        adapter="codex",
        get_run=lambda run_id: {
            "id": run_id,
            "status": "failed",
            "error_message": BACKGROUND_WORKER_START_ERROR,
            "task_verdict": {
                "status": "not_evaluated",
                "source": "run_status",
                "summary": "No evidence ledger entries are available yet.",
            },
        },
    )

    assert choice["action"] == "retry_lifecycle_failure"
    assert choice["choice_status"] == "terminal_retry"
    assert choice["linked_run_status"] == "failed"
    assert choice["linked_run_lifecycle_failure"] is True
    assert choice["recording_blocked_reason"] == "cannot accept lifecycle failure as a run result"
    assert choice["task_verdict_status"] == "not_evaluated"
    assert choice["runnable"] is True
    assert choice["next_slash_command"] == "/loopora-run option:agent_run:align_retry"
    assert choice["label_en"].startswith("Retry failed run start: Ship the focused starter experience.")


def test_agent_run_context_choice_keeps_legacy_lifecycle_failure_retry_without_task_verdict(tmp_path) -> None:
    repo = AgentRecoveryRepository(sessions=[], events_by_session={})
    session = {
        "id": "align_legacy_retry",
        "status": "running_loop",
        "workdir": str(tmp_path),
        "linked_run_id": "run_legacy_failed_start",
        "transcript": [{"role": "user", "content": "Ship the focused starter experience."}],
    }

    choice = agent_run_context_choice_from_session(
        repo,
        session,
        adapter="codex",
        get_run=lambda run_id: {
            "id": run_id,
            "status": "failed",
            "error_message": BACKGROUND_WORKER_START_ERROR,
        },
    )

    assert choice["action"] == "retry_lifecycle_failure"
    assert choice["linked_run_lifecycle_failure"] is True
    assert choice["recording_blocked_reason"] == "cannot accept lifecycle failure as a run result"
    assert choice["task_verdict_status"] == ""
    assert choice["next_slash_command"] == "/loopora-run option:agent_run:align_legacy_retry"


def test_agent_continuation_context_marks_lifecycle_failure_retry(tmp_path) -> None:
    layout = RunArtifactLayout(tmp_path / "run_failed_start")
    layout.initialize()
    previous_run = {
        "id": "run_failed_start",
        "status": "failed",
        "runs_dir": str(layout.run_dir),
        "error_message": BACKGROUND_WORKER_START_ERROR,
        "task_verdict": {
            "status": "not_evaluated",
            "source": "run_status",
            "summary": "No evidence ledger entries are available yet.",
            "buckets": {"unproven": [{"text": "This should not become retry focus."}]},
        },
    }

    context = agent_native_continuation_context_for_terminal_run(previous_run, layout)

    assert context["reason"] == "previous_lifecycle_failure_retry"
    assert context["previous_run_lifecycle_failure"] is True
    assert context["recording_blocked_reason"] == "cannot accept lifecycle failure as a run result"
    assert context["next_focus"] == []


def test_agent_run_context_choice_from_session_repairs_missing_run_and_failed_preview(tmp_path) -> None:
    repo = AgentRecoveryRepository(
        sessions=[],
        events_by_session={
            "align_failed": [
                {
                    "event_type": "alignment_bundle_sync_failed",
                    "payload": {"error": "candidate failed semantic lint", "bundle_path": "/tmp/failed-preview.yml"},
                }
            ]
        },
    )

    stale = agent_run_context_choice_from_session(
        repo,
        {
            "id": "align_stale",
            "status": "ready",
            "workdir": str(tmp_path),
            "linked_run_id": "run_missing",
        },
        adapter="codex",
        get_run=lambda _run_id: (_ for _ in ()).throw(LooporaError("missing run")),
    )
    failed = agent_run_context_choice_from_session(
        repo,
        {
            "id": "align_failed",
            "status": "failed",
            "workdir": str(tmp_path),
            "validation": {},
        },
        adapter="codex",
        payload={"source_path": "/workspace/loopora-plan.yml"},
        get_run=lambda _run_id: {},
    )

    assert stale["action"] == "stale_linked_run"
    assert stale["runnable"] is False
    assert failed["action"] == "repair_failed_preview"
    assert failed["validation_error"] == "candidate failed semantic lint"
    assert failed["plan_file_to_repair"] == "/workspace/loopora-plan.yml"
    assert failed["preview_plan_copy"] == "/tmp/failed-preview.yml"


def test_agent_run_context_choices_builds_bounded_deduplicated_recovery_projection(tmp_path) -> None:
    root = tmp_path / "project"
    repo = AgentRecoveryRepository(
        sessions=[
            {"id": "align_ready", "status": "ready", "workdir": str(root), "executor_kind": "codex"},
            {"id": "align_ready", "status": "ready", "workdir": str(root), "executor_kind": "codex"},
            {"id": "align_other", "status": "ready", "workdir": str(tmp_path / "other"), "executor_kind": "codex"},
        ],
        events_by_session={
            "align_ready": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "agent_entry", "adapter": "codex"},
                }
            ],
            "align_other": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "agent_entry", "adapter": "codex"},
                }
            ],
        },
    )

    choices = agent_run_context_choices(
        repo,
        root=root,
        adapter="codex",
        same_workdir=lambda workdir, expected: str(workdir) == str(expected),
        get_run=lambda _run_id: {},
    )

    assert [choice["option_id"] for choice in choices] == ["agent_run:align_ready"]
    assert choices[0]["action"] == "start_ready_preview"
