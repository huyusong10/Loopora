from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    LooporaConflictError,
    Path,
    _assert_missing_candidate_agent_review,
    _assert_not_fit_agent_review,
    _wait_for_alignment_status,
    pytest,
)
from loopora.service_alignment_session_lifecycle import alignment_thread_key

DEFAULT_TASK_MESSAGE = "Prepare a governed implementation loop from the host Agent context."


def test_agent_bundle_candidate_without_yaml_opens_prefill_without_starting_alignment(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    generated = create_missing_candidate(service, sample_workdir, DEFAULT_TASK_MESSAGE)

    assert (generated["ready"], generated["status"], generated["requires_web_alignment"], generated["requires_candidate_repair"]) == (False, "idle", True, False)
    assert_empty_candidate_fingerprint(generated)
    _assert_missing_candidate_agent_review(
        generated["session"]["agent_entry_review"],
        task_message=DEFAULT_TASK_MESSAGE,
    )
    transcript = generated["session"]["transcript"]
    assert transcript[0]["content"] == DEFAULT_TASK_MESSAGE
    assert transcript[-1]["role"] == "assistant"
    assert "Web review" in transcript[-1]["content"]
    assert "not a runnable Loop yet" in transcript[-1]["content"]
    assert "candidate plan file" in transcript[-1]["content"]
    assert "candidate YAML" not in transcript[-1]["content"]
    assert "Loopora fit" in transcript[-1]["content"]
    assert "execution strategy" in transcript[-1]["content"]
    assert "judgment tradeoffs" in transcript[-1]["content"]
    assert "local governance responsibilities" in transcript[-1]["content"]
    assert (generated["binding"]["requires_web_alignment"], generated["binding"]["requires_candidate_repair"]) == (True, False)
    assert_empty_candidate_fingerprint(generated["binding"])
    assert generated["preview_path"].startswith("/loops/new/bundle?alignment_session_id=")
    transcript_log = Path(generated["session"]["artifact_dir"]) / "conversation" / "transcript.jsonl"
    assert "Web review" in transcript_log.read_text(encoding="utf-8")
    events = service.list_alignment_events(generated["session"]["id"])
    candidate_event = agent_candidate_event(events)
    assert (candidate_event["payload"]["has_candidate_yaml"], candidate_event["payload"]["requires_web_alignment"], candidate_event["payload"]["requires_candidate_repair"]) == (False, True, False)
    assert_empty_candidate_fingerprint(candidate_event["payload"], ready=False)

    service.append_alignment_message(
        generated["session"]["id"],
        generated["session"]["agent_entry_review"]["suggested_reply"],
    )
    agreement = _wait_for_alignment_status(service, generated["session"]["id"], "waiting_user")
    assert agreement["alignment_stage"] == "agreement_ready"
    assert agreement.get("agent_entry_review", {}) == {}
    assert candidate_event["payload"]["ready_candidate_sha256"] == ""
    assert candidate_event["payload"]["ready_candidate_bytes"] == 0
    assert not any(event["event_type"] == "alignment_started" for event in events)
    assert_start_agent_loop_requires_web_review(service, sample_workdir, "/loopora-plan")


def test_agent_bundle_candidate_missing_yaml_can_complete_interactive_review_then_run(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    generated = create_missing_candidate(service, sample_workdir, DEFAULT_TASK_MESSAGE)
    assert generated["binding"]["requires_web_alignment"] is True
    assert_start_agent_loop_requires_web_review(service, sample_workdir, "/loopora-plan")

    service.append_alignment_message(
        generated["session"]["id"],
        generated["session"]["agent_entry_review"]["suggested_reply"],
    )
    agreement = _wait_for_alignment_status(service, generated["session"]["id"], "waiting_user")
    assert agreement["alignment_stage"] == "agreement_ready"
    assert not Path(agreement["bundle_path"]).exists()

    service.append_alignment_message(generated["session"]["id"], "确认，采用这份工作协议。")
    ready = _wait_for_alignment_status(service, generated["session"]["id"], "ready")
    assert ready["validation"]["ok"] is True
    assert ready.get("agent_entry_review", {}) == {}
    assert Path(ready["bundle_path"]).exists()

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["execution_plane"] == "agent_native"
    assert started["started_new_run"] is True
    assert started["run"]["status"] == "awaiting_agent"
    assert started["next_step"]["step_id"] == "builder_step"
    assert started["binding"]["requires_web_alignment"] is False
    assert started["binding"]["alignment_status"] == "running_loop"
    assert started["binding"]["linked_run_id"] == started["run"]["id"]
    assert [item["action"] for item in started["binding"]["entry_invocations"][-2:]] == ["plan", "run"]


def test_agent_bundle_candidate_missing_yaml_plan_message_continues_same_alignment_session(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    generated = create_missing_candidate(service, sample_workdir, DEFAULT_TASK_MESSAGE)
    first_session_id = generated["session"]["id"]

    continued = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=generated["session"]["agent_entry_review"]["suggested_reply"],
            entry_source="codex_project_skill",
        )
    )

    assert continued["continued_alignment_session"] is True
    assert continued["session"]["id"] == first_session_id
    assert continued["status"] == "waiting_user"
    assert continued["session"]["alignment_stage"] == "agreement_ready"
    assert continued["session"].get("active_child_pid") in {None, ""}
    assert alignment_thread_key(first_session_id) not in service._threads
    assert continued["requires_web_alignment"] is True
    assert continued["binding"]["alignment_session_id"] == first_session_id
    assert continued["binding"]["requires_web_alignment"] is True
    assert [item["action"] for item in continued["binding"]["entry_invocations"][-2:]] == ["plan", "plan"]

    confirmed = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="确认，采用这份工作协议。",
            entry_source="codex_project_skill",
        )
    )

    assert confirmed["continued_alignment_session"] is True
    assert confirmed["session"]["id"] == first_session_id
    assert confirmed["ready"] is True
    assert confirmed["status"] == "ready"
    assert confirmed["requires_web_alignment"] is False
    assert confirmed["binding"]["requires_web_alignment"] is False
    assert Path(confirmed["session"]["bundle_path"]).exists()


def test_agent_bundle_candidate_missing_yaml_new_task_message_starts_new_alignment_session(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    first = create_missing_candidate(service, sample_workdir, DEFAULT_TASK_MESSAGE)
    second = create_missing_candidate(service, sample_workdir, "Prepare a second governed implementation loop.")

    assert second.get("continued_alignment_session") is not True
    assert second["session"]["id"] != first["session"]["id"]
    assert second["session"]["transcript"][0]["content"] == "Prepare a second governed implementation loop."
    assert second["status"] == "idle"
    assert second["requires_web_alignment"] is True


def test_agent_bundle_candidate_without_yaml_uses_chinese_prefill_message(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    generated = create_missing_candidate(service, sample_workdir, "为退款自助流程准备一个需要多轮证据治理的 Loop。")

    message = generated["session"]["transcript"][-1]["content"]
    assert "候选方案文件" in message
    assert "不会伪装成可运行 Loop" in message
    assert "执行策略" in message
    assert "判断取舍" in message
    assert "本地治理责任" in message
    assert "candidate plan file" not in message


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("This is a one-off task; no Loopora loop is needed.", "one-off fix"),
        ("这是一次性任务，不要长期循环，直接处理完即可。", "不需要后续新证据"),
        ("The stable proof harness already fully captures the judgment.", "benchmark/test-harness-only path"),
    ],
)
def test_agent_bundle_candidate_without_yaml_explains_not_fit_prefill(
    service_factory,
    sample_workdir: Path,
    message: str,
    expected: str,
) -> None:
    service = service_factory(scenario="success")

    generated = create_missing_candidate(service, sample_workdir, message)

    transcript_message = generated["session"]["transcript"][-1]["content"]
    assert (generated["ready"], generated["requires_web_alignment"], generated["requires_candidate_repair"], generated["loopora_fit_contradiction"], generated["binding"]["loopora_fit_contradiction"]) == (False, True, False, True, True)
    _assert_not_fit_agent_review(generated["session"]["agent_entry_review"])
    assert "Web review" in transcript_message
    assert "not a runnable Loop yet" in transcript_message or "不会伪装成可运行 Loop" in transcript_message
    assert expected in transcript_message
    assert "success criteria" not in transcript_message
    candidate_event = agent_candidate_event(service.list_alignment_events(generated["session"]["id"]))
    assert candidate_event["payload"]["has_candidate_yaml"] is False
    assert candidate_event["payload"]["loopora_fit_contradiction"] is True
    assert_start_agent_loop_requires_web_review(
        service,
        sample_workdir,
        "one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only",
        "GateKeeper value",
    )


def create_missing_candidate(service, sample_workdir: Path, message: str) -> dict:
    request = AgentBundleCandidateRequest(adapter="codex", workdir=sample_workdir, message=message, entry_source="codex_project_skill")
    return service.create_agent_bundle_candidate(request)


def assert_empty_candidate_fingerprint(payload: dict, *, ready: bool = True) -> None:
    assert (payload["candidate_sha256"], payload["candidate_bytes"]) == ("", 0)
    if ready:
        assert (payload["ready_candidate_sha256"], payload["ready_candidate_bytes"]) == ("", 0)


def agent_candidate_event(events: list[dict]) -> dict:
    return next(event for event in events if event["event_type"] == "agent_candidate_received")


def assert_start_agent_loop_requires_web_review(service, sample_workdir: Path, *expected: str) -> None:
    with pytest.raises(LooporaConflictError) as excinfo:
        service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    error = str(excinfo.value)
    assert "needs Web review before /loopora-run" in error
    for marker in expected:
        assert marker in error
