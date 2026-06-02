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
