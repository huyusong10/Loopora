from __future__ import annotations

from agent_bundle_candidates_test_support import (
    AgentBundleCandidateRequest,
    CliRunner,
    LooporaConflictError,
    LooporaError,
    Path,
    _assert_labeled_loopora_agent_command,
    _assert_missing_candidate_agent_review,
    _assert_not_fit_agent_review,
    _assert_web_review_json_payload,
    _assert_web_review_plain_output,
    _error_text,
    _invoke_codex_plan,
    _wait_for_alignment_status,
    alignment_bundle_yaml,
    cli,
    cli_agent_runtime_support,
    json,
    pytest,
)


def test_agent_bundle_candidate_rejects_missing_workdir(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match="adapter project root does not exist"):
        service.create_agent_bundle_candidate(
            AgentBundleCandidateRequest(
                adapter="codex",
                workdir=tmp_path / "missing-project",
                message="Prepare a Loop for a project that is not present.",
                bundle_yaml=alignment_bundle_yaml(str(tmp_path / "missing-project")),
            )
        )


def test_agent_bundle_candidate_without_yaml_opens_prefill_without_starting_alignment(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prepare a governed implementation loop from the host Agent context.",
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "idle"
    assert generated["requires_web_alignment"] is True
    assert generated["requires_candidate_repair"] is False
    assert generated["candidate_sha256"] == ""
    assert generated["candidate_bytes"] == 0
    assert generated["ready_candidate_sha256"] == ""
    assert generated["ready_candidate_bytes"] == 0
    _assert_missing_candidate_agent_review(
        generated["session"]["agent_entry_review"],
        task_message="Prepare a governed implementation loop from the host Agent context.",
    )
    transcript = generated["session"]["transcript"]
    assert transcript[0]["content"] == "Prepare a governed implementation loop from the host Agent context."
    assert transcript[-1]["role"] == "assistant"
    assert "Web review" in transcript[-1]["content"]
    assert "not a runnable Loop yet" in transcript[-1]["content"]
    assert "candidate plan file" in transcript[-1]["content"]
    assert "candidate YAML" not in transcript[-1]["content"]
    assert "Loopora fit" in transcript[-1]["content"]
    assert "execution strategy" in transcript[-1]["content"]
    assert "judgment tradeoffs" in transcript[-1]["content"]
    assert "local governance responsibilities" in transcript[-1]["content"]
    assert generated["binding"]["requires_web_alignment"] is True
    assert generated["binding"]["requires_candidate_repair"] is False
    assert generated["binding"]["candidate_sha256"] == ""
    assert generated["binding"]["candidate_bytes"] == 0
    assert generated["binding"]["ready_candidate_sha256"] == ""
    assert generated["binding"]["ready_candidate_bytes"] == 0
    assert generated["preview_path"].startswith("/loops/new/bundle?alignment_session_id=")
    transcript_log = Path(generated["session"]["artifact_dir"]) / "conversation" / "transcript.jsonl"
    assert "Web review" in transcript_log.read_text(encoding="utf-8")
    events = service.list_alignment_events(generated["session"]["id"])
    candidate_event = next(event for event in events if event["event_type"] == "agent_candidate_received")
    assert candidate_event["payload"]["has_candidate_yaml"] is False
    assert candidate_event["payload"]["requires_web_alignment"] is True
    assert candidate_event["payload"]["requires_candidate_repair"] is False
    assert candidate_event["payload"]["candidate_sha256"] == ""
    assert candidate_event["payload"]["candidate_bytes"] == 0

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
    with pytest.raises(LooporaConflictError) as excinfo:
        service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    assert "needs Web review before /loopora-run" in str(excinfo.value)
    assert "/loopora-plan" in str(excinfo.value)


def test_agent_bundle_candidate_without_yaml_uses_chinese_prefill_message(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="为退款自助流程准备一个需要多轮证据治理的 Loop。",
            entry_source="codex_project_skill",
        )
    )

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

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=message,
            entry_source="codex_project_skill",
        )
    )

    transcript_message = generated["session"]["transcript"][-1]["content"]
    assert generated["ready"] is False
    assert generated["requires_web_alignment"] is True
    assert generated["requires_candidate_repair"] is False
    assert generated["loopora_fit_contradiction"] is True
    assert generated["binding"]["loopora_fit_contradiction"] is True
    _assert_not_fit_agent_review(generated["session"]["agent_entry_review"])
    assert "Web review" in transcript_message
    assert "not a runnable Loop yet" in transcript_message or "不会伪装成可运行 Loop" in transcript_message
    assert expected in transcript_message
    assert "success criteria" not in transcript_message
    events = service.list_alignment_events(generated["session"]["id"])
    candidate_event = next(event for event in events if event["event_type"] == "agent_candidate_received")
    assert candidate_event["payload"]["has_candidate_yaml"] is False
    assert candidate_event["payload"]["loopora_fit_contradiction"] is True
    with pytest.raises(LooporaConflictError) as excinfo:
        service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    assert "needs Web review before /loopora-run" in str(excinfo.value)
    assert "one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only" in str(excinfo.value)
    assert "GateKeeper value" in str(excinfo.value)


def test_agent_bundle_candidate_without_yaml_requires_task_summary(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")

    with pytest.raises(LooporaError, match="--message task summary"):
        service.create_agent_bundle_candidate(
            AgentBundleCandidateRequest(
                adapter="codex",
                workdir=sample_workdir,
                entry_source="codex_project_skill",
            )
        )


def test_agent_loop_clears_web_review_requirement_after_fallback_becomes_ready(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prepare a governed implementation loop from the host Agent context.",
            entry_source="codex_project_skill",
        )
    )
    assert generated["binding"]["requires_web_alignment"] is True
    Path(generated["session"]["bundle_path"]).write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    synced = service.sync_alignment_bundle_from_file(generated["session"]["id"])
    assert synced["session"]["status"] == "ready"
    assert synced["session"].get("agent_entry_review", {}) == {}

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["execution_plane"] == "agent_native"
    assert started["started_new_run"] is True
    assert started["session"].get("agent_entry_review", {}) == {}
    assert started["binding"]["requires_web_alignment"] is False
    assert started["binding"]["alignment_status"] == "running_loop"
    assert started["binding"]["linked_run_id"] == started["run"]["id"]


def test_agent_loop_clears_not_fit_fallback_after_web_review_becomes_ready(
    service_factory,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="There is no need for a Loopora loop here; just answer directly.",
            entry_source="codex_project_skill",
        )
    )
    assert generated["binding"]["requires_web_alignment"] is True
    assert generated["binding"]["loopora_fit_contradiction"] is True
    Path(generated["session"]["bundle_path"]).write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    synced = service.sync_alignment_bundle_from_file(generated["session"]["id"])
    assert synced["session"]["status"] == "ready"
    assert synced["session"].get("agent_entry_review", {}) == {}

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["execution_plane"] == "agent_native"
    assert started["started_new_run"] is True
    assert started["session"].get("agent_entry_review", {}) == {}
    assert started["binding"]["requires_web_alignment"] is False
    assert started["binding"]["loopora_fit_contradiction"] is False
    events = service.list_alignment_events(generated["session"]["id"])
    candidate_event = next(event for event in events if event["event_type"] == "agent_candidate_received")
    assert candidate_event["payload"]["loopora_fit_contradiction"] is True


def test_cli_agent_gen_without_bundle_reports_web_alignment_needed(sample_workdir: Path) -> None:
    runner = CliRunner()
    task_message = "Prepare a governed implementation loop."

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        entry_source="codex_project_skill",
    )

    assert result.exit_code == 0, result.stdout
    _assert_web_review_plain_output(result.stdout, task_message=task_message)

    json_task_message = "Prepare a second governed implementation loop."
    json_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=json_task_message,
        entry_source="codex_project_skill",
        json_output=True,
    )

    assert json_result.exit_code == 0, json_result.stdout
    _assert_web_review_json_payload(json.loads(json_result.stdout), task_message=json_task_message)


def test_cli_agent_gen_reports_auto_started_web_review_url(sample_workdir: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        cli_agent_runtime_support,
        "ensure_local_web_service",
        lambda: {"base_url": "http://127.0.0.1:9876", "reused": False, "started": True, "port": 9876},
    )

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--entry-source",
            "codex_project_skill",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview needs Web review" in result.stdout
    assert "review_status: not runnable; no candidate plan file was submitted" in result.stdout
    assert "task_anchor_status: task anchor preserved from /loopora-plan" in result.stdout
    assert "review_scope: review_focus lists Loop surfaces to compile from the task anchor, not missing chat input" in result.stdout
    assert "review_recommended_action: Continue evidence-first review (Recommended)" in result.stdout
    assert "review_focus:" in result.stdout
    assert "preview_url: http://127.0.0.1:9876/loops/new/bundle?alignment_session_id=" in result.stdout
    assert "after_review_slash_command: /loopora-run" in result.stdout
    _assert_labeled_loopora_agent_command(result.stdout, "after_review_cli_command", "run")
    _assert_labeled_loopora_agent_command(result.stdout, "after_review_command", "run")
    assert "web: started http://127.0.0.1:9876" in result.stdout


def test_cli_agent_loop_after_web_review_fallback_reprints_review_url_and_focus(sample_workdir: Path, monkeypatch) -> None:
    runner = CliRunner()
    gen_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop with later evidence and GateKeeper review.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )
    monkeypatch.setattr(
        cli_agent_runtime_support,
        "ensure_local_web_service",
        lambda: {"base_url": "http://127.0.0.1:9988", "reused": False, "started": True, "port": 9988},
    )

    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir)])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert loop_result.exit_code == 1
    output_text = loop_result.output
    assert "loop_recovery: finish the current Web review before /loopora-run can start" in output_text
    assert "review_status: not runnable; no candidate plan file was submitted" in output_text
    assert "task_anchor_status: task anchor preserved from /loopora-plan" in output_text
    assert "review_scope: review_focus lists Loop surfaces to compile from the task anchor, not missing chat input" in output_text
    assert "review_focus:" in output_text
    assert "Success surface:" in output_text
    assert "Fake-done risks:" in output_text
    assert "Evidence expectations:" in output_text
    assert "review_recommended_action: Continue evidence-first review (Recommended)" in output_text
    assert "next_review_step: open the preview URL" in output_text
    assert "after_review_ready: return to this Agent session and run /loopora-run" in output_text
    assert "after_review_slash_command: /loopora-run" in output_text
    _assert_labeled_loopora_agent_command(output_text, "after_review_cli_command", "run")
    _assert_labeled_loopora_agent_command(output_text, "after_review_command", "run")
    assert "preview_url: http://127.0.0.1:9988/loops/new/bundle?alignment_session_id=" in output_text
    assert "web: started http://127.0.0.1:9988" in output_text
    assert "Traceback" not in output_text
    assert _error_text(loop_result) == ""
    assert "cli.command.failed" not in output_text
    assert "current status: idle" not in output_text
