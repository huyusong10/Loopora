from __future__ import annotations

from loopora.service_alignment_run_recovery import (
    agent_candidate_events_include_yaml,
    agent_entry_candidate_adapter,
    agent_entry_candidate_payload,
    agent_entry_launch_projection,
    agent_entry_review_projection,
    agent_exact_binding_recovery_action,
    agent_failed_preview_choice_repair_fields,
    agent_redacted_context_binding,
    agent_recovery_agent_entry_candidate_event,
    agent_recovery_agent_entry_ready_event,
    agent_recovery_alignment_sessions,
    agent_recovery_bundle_sync_failed_event,
    agent_recovery_session_has_candidate_yaml,
    agent_run_context_choice_from_session,
    agent_run_context_choice_payload,
    agent_run_context_choices,
    agent_run_context_choice_summary,
    agent_run_context_next_action,
    agent_run_context_source_entries,
    latest_agent_entry_event,
    latest_alignment_bundle_sync_failed_event,
)
from loopora.service_types import LooporaError


class _AgentRecoveryRepository:
    def __init__(self, sessions: list[dict], events_by_session: dict[str, list[dict]], *, expose_all_sessions: bool = True):
        self.sessions = sessions
        self.events_by_session = events_by_session
        self.expose_all_sessions = expose_all_sessions
        self.used_all_sessions = False
        self.list_sessions_limits: list[int] = []
        self.event_limits: list[tuple[str, int]] = []

    def list_all_alignment_sessions(self) -> list[dict]:
        if not self.expose_all_sessions:
            raise AttributeError("list_all_alignment_sessions disabled for this test")
        self.used_all_sessions = True
        return self.sessions

    def list_alignment_sessions(self, *, limit: int = 100) -> list[dict]:
        self.list_sessions_limits.append(limit)
        return self.sessions[:limit]

    def list_alignment_events(self, session_id: str, *, limit: int = 200) -> list[dict]:
        self.event_limits.append((session_id, limit))
        return self.events_by_session.get(session_id, [])[:limit]


class _FallbackAgentRecoveryRepository:
    def __init__(self, sessions: list[dict], events_by_session: dict[str, list[dict]]):
        self.sessions = sessions
        self.events_by_session = events_by_session
        self.list_sessions_limits: list[int] = []

    def list_alignment_sessions(self, *, limit: int = 100) -> list[dict]:
        self.list_sessions_limits.append(limit)
        return self.sessions[:limit]

    def list_alignment_events(self, session_id: str, *, limit: int = 200) -> list[dict]:
        return self.events_by_session.get(session_id, [])[:limit]


def test_agent_recovery_alignment_sessions_prefers_full_repository_lookup() -> None:
    repo = _AgentRecoveryRepository(
        sessions=[{"id": "align_1"}, {"id": "align_2"}],
        events_by_session={},
    )

    assert agent_recovery_alignment_sessions(repo) == [{"id": "align_1"}, {"id": "align_2"}]
    assert repo.used_all_sessions is True
    assert repo.list_sessions_limits == []


def test_agent_recovery_alignment_sessions_falls_back_to_bounded_lookup() -> None:
    repo = _FallbackAgentRecoveryRepository(
        sessions=[{"id": "align_1"}, {"id": "align_2"}],
        events_by_session={},
    )

    assert agent_recovery_alignment_sessions(repo) == [{"id": "align_1"}, {"id": "align_2"}]
    assert repo.list_sessions_limits == [100]


def test_agent_recovery_event_lookup_uses_agent_entry_semantics() -> None:
    repo = _AgentRecoveryRepository(
        sessions=[],
        events_by_session={
            "align_1": [
                {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "web", "id": "ignored"}},
                {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "agent_entry", "id": "plan"}},
                {"event_type": "agent_candidate_ready_content", "payload": {"candidate_origin": "agent_entry", "id": "ready"}},
                {"event_type": "alignment_bundle_sync_failed", "payload": {"error": "failed"}},
            ]
        },
    )

    assert agent_recovery_agent_entry_candidate_event(repo, "align_1")["payload"]["id"] == "plan"
    assert agent_recovery_agent_entry_ready_event(repo, "align_1")["payload"]["id"] == "ready"
    assert agent_recovery_bundle_sync_failed_event(repo, "align_1")["payload"]["error"] == "failed"
    assert repo.event_limits == [("align_1", 50), ("align_1", 50), ("align_1", 50)]


def test_agent_recovery_session_has_candidate_yaml_reads_bounded_events() -> None:
    repo = _AgentRecoveryRepository(
        sessions=[],
        events_by_session={
            "align_1": [
                {"event_type": "agent_candidate_received", "payload": {"has_candidate_yaml": True}},
            ]
        },
    )

    assert agent_recovery_session_has_candidate_yaml(repo, "align_1") is True
    assert repo.event_limits == [("align_1", 50)]


def test_agent_run_context_source_entries_filter_by_workdir_adapter_and_agent_entry_event(tmp_path) -> None:
    root = tmp_path / "project"
    other = tmp_path / "other"
    sessions = [
        {"id": "align_codex", "workdir": str(root), "executor_kind": "claude"},
        {"id": "align_claude", "workdir": str(root), "executor_kind": "claude"},
        {"id": "align_other_workdir", "workdir": str(other), "executor_kind": "codex"},
        {"id": "align_web_candidate", "workdir": str(root), "executor_kind": "codex"},
    ]
    repo = _AgentRecoveryRepository(
        sessions=sessions,
        events_by_session={
            "align_codex": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "agent_entry", "adapter": "codex", "entry_source": "codex_project_skill"},
                }
            ],
            "align_claude": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "agent_entry", "entry_source": "claude_project_command"},
                }
            ],
            "align_other_workdir": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "agent_entry", "adapter": "codex"},
                }
            ],
            "align_web_candidate": [
                {
                    "event_type": "agent_candidate_received",
                    "payload": {"candidate_origin": "web", "adapter": "codex"},
                }
            ],
        },
    )

    entries = agent_run_context_source_entries(
        repo,
        root=root,
        adapter="codex",
        same_workdir=lambda workdir, expected: str(workdir) == str(expected),
    )

    assert [(session["id"], payload["entry_source"], adapter) for session, payload, adapter in entries] == [
        ("align_codex", "codex_project_skill", "codex")
    ]


def test_agent_run_context_next_action_maps_terminal_verdicts_and_stale_links() -> None:
    assert (
        agent_run_context_next_action(
            session_status="ready",
            linked_run_id="run_passed",
            linked_run_status="succeeded",
            task_verdict_status="passed",
        )
        == "replay_terminal_pass"
    )
    assert (
        agent_run_context_next_action(
            session_status="ready",
            linked_run_id="run_unproven",
            linked_run_status="succeeded",
            task_verdict_status="continue_required",
        )
        == "continue_terminal_evidence"
    )
    assert (
        agent_run_context_next_action(
            session_status="ready",
            linked_run_id="run_missing",
            linked_run_found=False,
        )
        == "stale_linked_run"
    )


def test_agent_run_context_choice_payload_separates_runnable_and_repair_commands(tmp_path) -> None:
    session = {
        "id": "align_ready",
        "status": "ready",
        "workdir": str(tmp_path),
        "updated_at": "2026-01-01T00:00:00+00:00",
    }

    runnable = agent_run_context_choice_payload(
        session,
        adapter="codex",
        payload={"entry_source": "codex_project_skill", "host_context_id": "thread-a"},
        title="Ready preview",
        next_action="start_ready_preview",
    )
    repair = agent_run_context_choice_payload(
        {**session, "status": "failed"},
        adapter="codex",
        title="Failed preview",
        next_action="repair_failed_preview",
    )

    assert runnable["runnable"] is True
    assert runnable["choice_status"] == "ready_preview"
    assert runnable["next_command"] == "/loopora-run option:agent_run:align_ready"
    assert "--source-option-id agent_run:align_ready" in runnable["next_cli_command"]
    assert runnable["entry_source"] == "codex_project_skill"
    assert runnable["host_context_id"] == "thread-a"
    assert repair["runnable"] is False
    assert repair["next_plan_command"] == "/loopora-plan"
    assert repair["next_command"] == ""
    assert repair["next_cli_command"] == ""


def test_agent_run_context_choice_summary_counts_only_dict_choices() -> None:
    summary = agent_run_context_choice_summary(
        [
            {"runnable": True},
            {"runnable": False},
            "not-a-choice",
            {},
        ]
    )

    assert summary["choice_count"] == 3
    assert summary["runnable_choice_count"] == 2
    assert summary["non_runnable_choice_count"] == 1
    assert "runnable contexts" in summary["selection_hint"]


def test_agent_run_context_choice_from_session_reads_linked_run_task_verdict(tmp_path) -> None:
    repo = _AgentRecoveryRepository(sessions=[], events_by_session={})
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


def test_agent_run_context_choice_from_session_repairs_missing_run_and_failed_preview(tmp_path) -> None:
    repo = _AgentRecoveryRepository(
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
    repo = _AgentRecoveryRepository(
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


def test_agent_entry_candidate_payload_and_adapter_preserve_event_priority() -> None:
    payload = agent_entry_candidate_payload({"payload": {"adapter": "codex", "entry_source": "codex_project_skill"}})

    assert payload == {"adapter": "codex", "entry_source": "codex_project_skill"}
    assert agent_entry_candidate_payload({"payload": "not-a-dict"}) == {}
    assert agent_entry_candidate_adapter({"executor_kind": "claude"}, payload) == "codex"
    assert agent_entry_candidate_adapter({"executor_kind": "claude"}, {}) == "claude"


def test_agent_entry_review_projection_exposes_web_review_decision_payload() -> None:
    session = {
        "id": "align_1",
        "status": "idle",
        "alignment_stage": "clarifying",
        "executor_kind": "codex",
        "transcript": [{"role": "user", "content": "为退款治理准备 Loop。"}],
    }
    candidate_event = {
        "payload": {
            "candidate_origin": "agent_entry",
            "requires_web_alignment": True,
            "requires_candidate_repair": False,
            "has_candidate_yaml": False,
            "adapter": "codex",
            "entry_source": "codex_project_skill",
            "candidate_bytes": "bad",
        }
    }

    review = agent_entry_review_projection(
        session,
        candidate_event=candidate_event,
        task_message="为退款治理准备 Loop。",
        missing_judgment_item_ids=["success_surface"],
    )

    assert review["source"] == "agent_entry"
    assert review["review_mode"] == "missing_candidate_plan"
    assert review["not_runnable"] is True
    assert review["candidate_bytes"] == 0
    assert review["missing_judgment_item_ids"] == ["success_surface"]
    assert review["decision_options"][0]["id"] == "continue_web_review_evidence_first"
    assert review["decision_options"][0]["recommended"] is True
    assert "证据优先" in review["suggested_reply"]
    assert agent_entry_review_projection(
        {**session, "working_agreement": {"summary": "already started"}},
        candidate_event=candidate_event,
        task_message="为退款治理准备 Loop。",
        missing_judgment_item_ids=["success_surface"],
    ) == {}


def test_agent_entry_launch_projection_prefers_ready_event_fingerprint(tmp_path) -> None:
    candidate_event = {
        "payload": {
            "candidate_origin": "agent_entry",
            "adapter": "codex",
            "entry_source": "codex_project_skill",
            "host_context_id": "thread-a",
            "candidate_sha256": "candidate-sha",
            "candidate_bytes": 12,
            "ready_candidate_sha256": "stale-ready-sha",
            "ready_candidate_bytes": 11,
        }
    }
    ready_event = {
        "payload": {
            "ready_candidate_sha256": "ready-sha",
            "ready_candidate_bytes": 42,
        }
    }

    launch = agent_entry_launch_projection(
        {"id": "align_1", "workdir": str(tmp_path), "executor_kind": "codex"},
        candidate_event=candidate_event,
        ready_event=ready_event,
    )

    assert launch["source"] == "agent_entry"
    assert launch["slash_command"] == "/loopora-run"
    assert launch["loop_command"].endswith("--json")
    assert "--context-id thread-a" in launch["loop_command"]
    assert launch["ready_candidate_sha256"] == "ready-sha"
    assert launch["ready_candidate_bytes"] == 42


def test_agent_exact_binding_recovery_action_maps_choice_state() -> None:
    assert agent_exact_binding_recovery_action({"linked_run_id": "run_1", "alignment_status": "ready"}) == "resume_run"
    assert agent_exact_binding_recovery_action({"linked_run_id": "", "alignment_status": "ready"}) == "start_ready_preview"
    assert agent_exact_binding_recovery_action({"linked_run_id": "", "alignment_status": "imported"}) == "start_ready_preview"
    assert agent_exact_binding_recovery_action({"linked_run_id": "", "alignment_status": "failed"}) == "blocked"


def test_agent_failed_preview_repair_fields_prioritize_user_source_and_validation_error() -> None:
    fields = agent_failed_preview_choice_repair_fields(
        {
            "id": "align_failed",
            "status": "failed",
            "error_message": "session error",
            "validation": {
                "error": "validation error",
                "bundle_path": "/tmp/validation-preview.yaml",
            },
        },
        payload={"source_path": "/workspace/loopora-plan.yaml"},
        failed_payload={
            "error": "event error",
            "bundle_path": "/tmp/event-preview.yaml",
        },
    )

    assert fields["validation_error"] == "validation error"
    assert fields["plan_file_to_repair"] == "/workspace/loopora-plan.yaml"
    assert fields["preview_plan_copy"] == "/tmp/validation-preview.yaml"
    assert fields["next_repair_step"].startswith("repair the candidate plan file")


def test_agent_failed_preview_repair_fields_fall_back_to_event_payload_and_omit_empty_fields() -> None:
    event_fields = agent_failed_preview_choice_repair_fields(
        {"id": "align_failed", "status": "failed"},
        failed_payload={
            "error": "event error",
            "bundle_path": "/tmp/event-preview.yaml",
        },
    )
    empty_fields = agent_failed_preview_choice_repair_fields({"id": "align_failed", "status": "failed"})

    assert event_fields["validation_error"] == "event error"
    assert event_fields["plan_file_to_repair"] == "/tmp/event-preview.yaml"
    assert event_fields["preview_plan_copy"] == "/tmp/event-preview.yaml"
    assert "validation_error" not in empty_fields
    assert "plan_file_to_repair" not in empty_fields
    assert "preview_plan_copy" not in empty_fields
    assert empty_fields == {
        "next_repair_step": "repair the candidate plan file, rerun /loopora-plan, then use /loopora-run only after the preview is ready"
    }


def test_agent_redacted_context_binding_keeps_recovery_fields_and_omits_non_contract_data() -> None:
    redacted = agent_redacted_context_binding(
        {
            "path": "/workspace/.loopora/agent-binding.json",
            "alignment_session_id": "align_1",
            "alignment_status": "ready",
            "linked_run_id": "run_1",
            "linked_loop_id": "loop_1",
            "linked_bundle_id": "bundle_1",
            "workdir": "/workspace/project",
            "host_context_id": "thread_1",
            "context_source": "codex_project_skill",
            "updated_at": "2026-01-01T00:00:00+00:00",
            "requires_web_alignment": False,
            "requires_candidate_repair": True,
            "loopora_fit_contradiction": "needs better evidence",
            "preview_path": "/loops/new/bundle?alignment_session_id=align_1",
            "run_path": "/runs/run_1",
            "raw_transcript": "private implementation detail",
            "random_field": "not a recovery contract",
        }
    )

    assert redacted == {
        "path": "/workspace/.loopora/agent-binding.json",
        "alignment_session_id": "align_1",
        "alignment_status": "ready",
        "linked_run_id": "run_1",
        "linked_loop_id": "loop_1",
        "linked_bundle_id": "bundle_1",
        "workdir": "/workspace/project",
        "host_context_id": "thread_1",
        "context_source": "codex_project_skill",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "requires_web_alignment": False,
        "requires_candidate_repair": True,
        "loopora_fit_contradiction": "needs better evidence",
        "preview_path": "/loops/new/bundle?alignment_session_id=align_1",
        "run_path": "/runs/run_1",
    }


def test_agent_redacted_context_binding_redacts_sensitive_allowed_values() -> None:
    redacted = agent_redacted_context_binding(
        {
            "path": "/workspace/.loopora/agent-binding.json?token=PATH_TOKEN_SECRET",
            "workdir": "Cookie: sid=WORKDIR_COOKIE_SECRET",
            "preview_path": "/preview?x-loopora-token=PREVIEW_TOKEN_SECRET",
        }
    )

    assert "PATH_TOKEN_SECRET" not in str(redacted)
    assert "WORKDIR_COOKIE_SECRET" not in str(redacted)
    assert "PREVIEW_TOKEN_SECRET" not in str(redacted)
    assert "<secret omitted>" in str(redacted)


def test_latest_alignment_bundle_sync_failed_event_returns_last_payload_event() -> None:
    latest = latest_alignment_bundle_sync_failed_event(
        [
            {"event_type": "alignment_bundle_sync_failed", "payload": {"error": "first"}},
            {"event_type": "alignment_bundle_sync_failed", "payload": "not-a-dict"},
            {"event_type": "other", "payload": {"error": "ignored"}},
            {"event_type": "alignment_bundle_sync_failed", "payload": {"error": "last"}},
        ]
    )

    assert latest["payload"] == {"error": "last"}
    assert latest_alignment_bundle_sync_failed_event([{"event_type": "other", "payload": {}}]) == {}


def test_latest_agent_entry_event_returns_last_matching_agent_entry_event() -> None:
    latest = latest_agent_entry_event(
        [
            {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "agent_entry", "id": "first"}},
            {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "web", "id": "ignored"}},
            {"event_type": "agent_candidate_received", "payload": "not-a-dict"},
            {"event_type": "agent_candidate_ready_content", "payload": {"candidate_origin": "agent_entry", "id": "ready"}},
            {"event_type": "agent_candidate_received", "payload": {"candidate_origin": "agent_entry", "id": "last"}},
        ],
        "agent_candidate_received",
    )

    assert latest["payload"]["id"] == "last"
    assert latest_agent_entry_event([{"event_type": "agent_candidate_received", "payload": {"candidate_origin": "web"}}], "agent_candidate_received") == {}


def test_agent_candidate_events_include_yaml_requires_received_payload_flag() -> None:
    assert agent_candidate_events_include_yaml(
        [
            {"event_type": "agent_candidate_received", "payload": {"has_candidate_yaml": False}},
            {"event_type": "agent_candidate_ready_content", "payload": {"has_candidate_yaml": True}},
            {"event_type": "agent_candidate_received", "payload": "not-a-dict"},
            {"event_type": "agent_candidate_received", "payload": {"has_candidate_yaml": True}},
        ]
    )
    assert not agent_candidate_events_include_yaml(
        [
            {"event_type": "agent_candidate_ready_content", "payload": {"has_candidate_yaml": True}},
            {"event_type": "agent_candidate_received", "payload": {"has_candidate_yaml": False}},
        ]
    )
