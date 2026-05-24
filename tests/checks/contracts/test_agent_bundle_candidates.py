from __future__ import annotations

from agent_adapter_helpers import *

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

def test_cli_agent_loop_json_after_web_review_fallback_returns_structured_recovery(sample_workdir: Path) -> None:
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

    loop_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert gen_result.exit_code == 0, gen_result.stdout
    assert loop_result.exit_code == 1
    assert _error_text(loop_result) == ""
    payload = json.loads(loop_result.stdout)
    assert payload["ready"] is False
    assert payload["agent_loop_recovery_summary"]["review_status"] == "not runnable; no candidate plan file was submitted"
    assert payload["agent_loop_recovery_summary"]["task_anchor_status"].startswith("task anchor preserved from /loopora-plan")
    assert payload["agent_loop_recovery_summary"]["review_scope"] == (
        "review_focus lists Loop surfaces to compile from the task anchor, not missing chat input"
    )
    assert payload["requires_web_alignment"] is True
    assert payload["requires_candidate_repair"] is False
    assert payload["loop_recovery"] == "finish_web_review"
    assert payload["review_status"] == "not runnable; no candidate plan file was submitted"
    assert payload["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert payload["review_focus"]
    assert payload["task_anchor_status"].startswith("task anchor preserved from /loopora-plan")
    assert payload["task_anchor_preview"].startswith("Prepare a governed implementation loop")
    assert payload["review_scope"] == "review_focus lists Loop surfaces to compile from the task anchor, not missing chat input"
    assert payload["next_review_step"].startswith("open the preview URL")
    assert payload["after_review_ready"].startswith("return to this Agent session")
    assert payload["after_review_slash_command"] == "/loopora-run"
    _assert_loopora_agent_command(payload["after_review_cli_command"], "run")
    _assert_loopora_agent_command(payload["after_review_command"], "run")
    assert payload["binding"]["candidate_entry_source"] == "codex_project_skill"

def test_cli_agent_loop_selected_not_ready_option_returns_current_context_command(sample_workdir: Path) -> None:
    runner = CliRunner()
    gen_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-original-review",
            "--message",
            "Prepare a governed implementation loop with later evidence and GateKeeper review.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )
    assert gen_result.exit_code == 0, gen_result.stdout
    generated = json.loads(gen_result.stdout)
    option_id = f"agent_run:{generated['session']['id']}"
    assert generated["after_review_slash_command"] == "/loopora-run"
    assert "--context-id thread-original-review" in generated["after_review_cli_command"]
    assert "--context-id thread-original-review" in generated["after_review_command"]

    loop_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-selected-review",
            "--source-option-id",
            option_id,
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert loop_result.exit_code == 1
    assert _error_text(loop_result) == ""
    payload = json.loads(loop_result.stdout)
    assert payload["loop_recovery"] == "finish_web_review"
    assert payload["binding"]["selected_option_id"] == option_id
    assert payload["binding"]["host_context_id"] == "thread-selected-review"
    assert payload["after_review_slash_command"] == "/loopora-run"
    assert "--context-id thread-selected-review" in payload["after_review_cli_command"]
    assert "--context-id thread-original-review" not in payload["after_review_cli_command"]
    assert "--context-id thread-selected-review" in payload["after_review_command"]
    assert "--context-id thread-original-review" not in payload["after_review_command"]

def test_cli_agent_loop_json_without_plan_returns_structured_plan_first_recovery(
    service_factory,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    monkeypatch.setattr(cli, "create_service", lambda: service)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert _error_text(result) == ""
    payload = json.loads(result.stdout)
    assert next(iter(payload)) == "agent_loop_recovery_summary"
    summary = payload["agent_loop_recovery_summary"]
    assert summary["loop_recovery"] == "plan_first"
    assert summary["next_plan_command"] == "/loopora-plan"
    assert summary["required_inputs"] == ["task_goal", "fake_done_risks", "required_evidence", "judgment_tradeoffs"]
    assert summary["ask_user"].startswith("What long-running task should Loopora govern?")
    assert summary["question_action"]["kind"] == "ask_user"
    assert "official user-question" in summary["question_action"]["native_tool_policy"]
    assert summary["example_user_reply"].startswith("Build the account-deletion audit flow")
    assert (
        summary["task_message_template"]
        == "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert summary["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert summary["next"].startswith("Ask the user the ask_user question")
    assert payload["ready"] is False
    assert payload["loop_recovery"] == "plan_first"
    assert payload["next_plan_command"] == "/loopora-plan"
    assert payload["required_inputs"] == ["task_goal", "fake_done_risks", "required_evidence", "judgment_tradeoffs"]
    assert payload["ask_user"].startswith("What long-running task should Loopora govern?")
    assert payload["question_action"]["target"] == "main_agent_session"
    assert payload["example_user_reply"].startswith("Build the account-deletion audit flow")
    assert (
        payload["task_message_template"]
        == "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert payload["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(payload["debug_cli_example_command"], "plan", json_mode=False)
    assert "--message" in payload["debug_cli_example_command"]
    assert payload["next"].startswith("Ask the user the ask_user question")
    assert payload["context_resolution"]["action"] == "plan_first"
    assert payload["context_resolution"]["confidence"] == "no_binding"

def test_cli_agent_gen_without_bundle_reports_not_fit_fallback(sample_workdir: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "There is no need for a Loopora loop here; just answer directly.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview needs Web review" in result.stdout
    assert "not_fit:" in result.stdout
    assert "review_status: not runnable; Loopora fit needs to be redefined" in result.stdout
    assert "review_focus:" in result.stdout
    assert "Loopora fit: define later evidence, handoffs, or GateKeeper value" in result.stdout
    assert "one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only work" in result.stdout
    assert "GateKeeper value" in result.stdout
    assert "review_recommended_action: Skip Loop (Recommended)" in result.stdout
    assert "after_review_ready: return to this Agent session and run /loopora-run" in result.stdout
    _assert_codex_native_surface_plain(result.stdout)
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in result.stdout

def test_cli_agent_gen_without_bundle_json_reports_not_fit_fallback(sample_workdir: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "There is no need for a Loopora loop here; just answer directly.",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ready"] is False
    assert payload["requires_web_alignment"] is True
    assert payload["requires_candidate_repair"] is False
    assert payload["loopora_fit_contradiction"] is True
    assert payload["binding"]["loopora_fit_contradiction"] is True
    assert payload["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    _assert_codex_native_surface_summary(payload["agent_plan_summary"])
    assert payload["agent_plan_summary"]["review_status"] == "not runnable; Loopora fit needs to be redefined"
    assert payload["review_status"] == "not runnable; Loopora fit needs to be redefined"
    assert payload["review_focus"][0].startswith("Loopora fit: define later evidence")
    _assert_loopora_agent_command(payload["after_review_command"], "run")


def _assert_plan_message_required_summary(summary: dict) -> None:
    _assert_codex_native_surface_summary(summary)
    assert summary["ready"] is False
    assert summary["loop_recovery"] == "plan_message_required"
    assert summary["next_plan_command"] == "/loopora-plan"
    assert summary["required_inputs"] == [
        "task_goal",
        "fake_done_risks",
        "required_evidence",
        "judgment_tradeoffs",
    ]
    assert summary["ask_user"].startswith("What long-running task should Loopora govern?")
    assert summary["question_action"]["subagent_policy"].startswith("Do not ask user questions")
    assert "fake done would be UI-only deletion" in summary["example_user_reply"]
    assert summary["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert summary["next"] == "Ask the user the ask_user question, then rerun /loopora-plan with the user's task context."


def test_cli_agent_gen_without_bundle_rejects_missing_task_summary(sample_workdir: Path) -> None:
    runner = CliRunner()

    text_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert text_result.exit_code == 1
    assert _error_text(text_result) == ""
    assert "loop_recovery: provide task context before /loopora-plan can create a preview" in text_result.stdout
    assert "next_plan_command: /loopora-plan" in text_result.stdout
    assert "required_inputs:" in text_result.stdout
    assert "- task_goal" in text_result.stdout
    assert "- fake_done_risks" in text_result.stdout
    assert "- required_evidence" in text_result.stdout
    assert "- judgment_tradeoffs" in text_result.stdout
    assert "ask_user: What long-running task should Loopora govern?" in text_result.stdout
    assert "question_action: Use the host's official user-question or follow-up capability" in text_result.stdout
    assert "example_user_reply: Build the account-deletion audit flow;" in text_result.stdout
    assert (
        "task_message_template: Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
        in text_result.stdout
    )
    assert "first_task_message_example:" in text_result.stdout
    assert "After /loopora-plan, send: Goal:" in text_result.stdout
    assert "debug_cli_example_command:" in text_result.stdout
    _assert_labeled_loopora_agent_command(text_result.stdout, "debug_cli_example_command", "plan", json_mode=False)
    _assert_codex_native_surface_plain(text_result.stdout)
    assert "next: Ask the user the ask_user question" in text_result.stdout

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    assert next(iter(payload)) == "agent_plan_summary"
    _assert_plan_message_required_summary(payload["agent_plan_summary"])
    assert payload["ready"] is False
    assert payload["loop_recovery"] == "plan_message_required"
    assert payload["next_plan_command"] == "/loopora-plan"
    assert payload["required_inputs"] == [
        "task_goal",
        "fake_done_risks",
        "required_evidence",
        "judgment_tradeoffs",
    ]
    assert payload["ask_user"].startswith("What long-running task should Loopora govern?")
    assert payload["question_action"]["subagent_policy"].startswith("Do not ask user questions")
    assert "fake done would be UI-only deletion" in payload["example_user_reply"]
    assert (
        payload["task_message_template"]
        == "Goal: ...; Fake-done risks: ...; Required evidence: ...; Judgment tradeoffs: ..."
    )
    assert payload["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(payload["debug_cli_example_command"], "plan", json_mode=False)
    assert f"--workdir {sample_workdir.resolve()}" in payload["debug_cli_example_command"]
    assert "--message" in payload["debug_cli_example_command"]
    assert payload["next"] == "Ask the user the ask_user question, then rerun /loopora-plan with the user's task context."

def test_agent_adapter_preview_fallback_uses_web_review_language() -> None:
    root = Path(__file__).resolve().parents[3]
    sources = "\n".join(
        [
            (root / "src" / "loopora" / "agent_adapters.py").read_text(encoding="utf-8"),
            (root / "src" / "loopora" / "cli_agent_adapter_commands.py").read_text(encoding="utf-8"),
            (root / "src" / "loopora" / "cli_agent_native.py").read_text(encoding="utf-8"),
        ]
    )

    assert "Web review" in sources
    assert "Web alignment URL" not in sources
    assert "needs Web alignment" not in sources
    assert "more alignment before" not in sources

def test_cli_codex_gen_accepts_ready_bundle_without_starting_run(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file, expected = _write_ready_bundle(tmp_path, sample_workdir)
    runner = CliRunner()

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message="Ship contract inspection for implementation handoff.",
        bundle_file=bundle_file,
        json_output=True,
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    _assert_ready_plan_summary(payload)
    _assert_ready_plan_payload(payload, expected)
    _assert_ready_review_projection(payload["ready_review_projection"])
    assert payload["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert payload["review_before_loop"] == "confirm the preview carries these judgments before running /loopora-run"
    assert payload["ready_next_step"].startswith("return to this Agent session and run /loopora-run")
    assert payload["ready_slash_command"] == "/loopora-run"
    assert "loopora agent codex run" in payload["ready_cli_command"]
    assert "--json" in payload["ready_cli_command"]
    assert payload["ready_run_command"] == payload["ready_cli_command"]
    assert "run" not in payload

def test_cli_agent_gen_ready_output_points_back_to_same_agent_loop(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Ship contract inspection for implementation handoff.",
            "--bundle-file",
            str(bundle_file),
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview is ready" in result.stdout
    assert "next_agent_step: review the preview URL, then run /loopora-run in this same Agent session" in result.stdout
    assert "ready_review:" in result.stdout
    assert "loopora_fit:" in result.stdout
    assert "fake_done_risks:" in result.stdout
    assert "evidence_preferences:" in result.stdout
    assert "coverage_targets: 2 checks /" in result.stdout
    assert "judgment_projection: 13/13 mapped" in result.stdout
    assert "closure_gate: GateKeeper (evidence_refs_required)" in result.stdout
    assert "review_before_loop: confirm the preview carries these judgments before running /loopora-run" in result.stdout
    assert "ready_next_step: return to this Agent session and run /loopora-run" in result.stdout
    assert "ready_slash_command: /loopora-run" in result.stdout
    _assert_labeled_loopora_agent_command(result.stdout, "ready_cli_command", "run")
    _assert_labeled_loopora_agent_command(result.stdout, "ready_run_command", "run")
    _assert_codex_native_surface_plain(result.stdout)
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in result.stdout
    assert "run_url:" not in result.stdout
    assert "Loopora run:" not in result.stdout

def test_cli_agent_gen_rejects_candidate_bundle_without_task_summary(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--bundle-file",
            str(bundle_file),
            "--no-web",
        ],
    )

    assert result.exit_code == 1
    assert _error_text(result) == ""
    assert "loop_recovery: provide task context before /loopora-plan can create a preview" in result.stdout
    assert "required_inputs:" in result.stdout
    assert "- task_goal" in result.stdout
    assert "- required_evidence" in result.stdout

def test_cli_agent_gen_with_invalid_candidate_reports_repair_before_loop(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    task_message = "Build a governed refund self-service flow with authorization, audit, and payment failure evidence."
    runner = CliRunner()

    result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        bundle_file=bundle_file,
    )

    assert result.exit_code == 0, result.stdout
    _assert_invalid_candidate_repair_plain_output(result.stdout, task_message=task_message, bundle_file=bundle_file)

    json_result = _invoke_codex_plan(
        runner,
        sample_workdir,
        message=task_message,
        bundle_file=bundle_file,
        json_output=True,
    )

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    _assert_invalid_candidate_repair_payload(payload, task_message=task_message, bundle_file=bundle_file)

    run_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--no-web",
            "--json",
        ],
    )

    assert run_result.exit_code == 1
    assert _error_text(run_result) == ""
    _assert_invalid_candidate_run_recovery(
        run_result.stdout,
        task_message=task_message,
        validation_error=payload["validation_error"],
        repair_focus=payload["repair_focus"],
        bundle_file=bundle_file,
    )

def test_agent_plan_repair_focus_explains_semantic_projection_categories() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: agent-first candidate must project explicit host Agent success criteria "
        "into runnable surfaces: missing data/export/report"
    )

    assert hints[0] == "add these missing success criteria categories from --message to runnable plan surfaces: data/export/report"
    assert hints[1] == (
        "include those categories in spec Done When/Success Surface, role responsibilities, workflow intent, "
        "evidence preferences, and GateKeeper closure"
    )

def test_agent_plan_repair_focus_explains_multiple_semantic_projection_categories() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: agent-first candidate must project the host Agent task summary "
        "into runnable surfaces: missing soc2, vendor, rollout; "
        "agent-first candidate must project explicit host Agent fake-done risks into runnable surfaces: "
        "missing permission/audit, download/export-only; "
        "agent-first candidate must project explicit host Agent evidence preferences into runnable surfaces: "
        "missing audit/log, permission/auth"
    )

    assert "add these missing task objects from --message to runnable plan surfaces: soc2, vendor, rollout" in hints
    assert (
        "add these missing fake-done risks categories from --message to runnable plan surfaces: "
        "permission/audit, download/export-only"
    ) in hints
    assert (
        "add these missing evidence preferences categories from --message to runnable plan surfaces: "
        "audit/log, permission/auth"
    ) in hints
    assert "include those evidence modes in spec Evidence Preferences, Inspector responsibilities, workflow handoffs, and GateKeeper closure" in hints

def test_agent_plan_repair_focus_explains_common_semantic_lint_issues() -> None:
    hints = cli_agent_adapter_commands._validation_repair_hints(
        "bundle semantic lint failed: "
        "collaboration_summary must explain why this task needs multi-round Loopora governance; "
        "spec must include at least one Success Surface bullet; "
        "spec Residual Risk guidance must name accepted risk handling or fail closed"
    )

    assert (
        "explain in collaboration_summary what later evidence, reviews, handoffs, or GateKeeper rounds add beyond one Agent pass"
        in hints
    )
    assert "add # Success Surface bullets that make the task judgment reviewable and runnable" in hints
    assert "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions" in hints

def test_cli_agent_loop_plain_output_discloses_resumed_existing_run(capsys) -> None:
    cli_agent_adapter_commands._print_agent_loop_result(
        {
            "run": {"id": "run_resume", "status": "awaiting_agent"},
            "run_path": "/runs/run_resume",
            "started_new_run": False,
            "complete": False,
        },
        json_output=False,
    )

    output = capsys.readouterr().out

    assert "Loopora run: run_resume" in output
    assert "run_start: resumed_existing_agent_native_run" in output

def test_cli_agent_gen_json_repair_focus_explains_structural_plan_errors(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bad-bundle.yml"
    bundle_file.write_text("version: 1\nspec:\n  name: Refund admin\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Build a refund admin workflow with audit and provider-failure evidence.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["loop_recovery"] == "repair_candidate_plan_file"
    assert payload["validation_error"] == "bundle metadata.name is required"
    assert "add metadata.name so the plan has a stable reviewable identity" in payload["repair_focus"]

def test_cli_agent_gen_json_repair_focus_explains_semantic_lint_issues(tmp_path: Path, sample_workdir: Path) -> None:
    payload = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    payload["collaboration_summary"] = "Coordinate a starter slice."
    markdown = payload["spec"]["markdown"]
    markdown = markdown.replace(
        "# Success Surface\n\n- The primary user flow is understandable, maintainable, and easy to extend after the first pass.\n\n",
        "",
    )
    markdown = markdown.replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; "
        "fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk remains.",
    )
    payload["spec"]["markdown"] = markdown
    bundle_file = tmp_path / "semantic-lint-bundle.yml"
    bundle_file.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Ship the focused starter experience in the target workdir with evidence and GateKeeper review.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    output = json.loads(result.stdout)
    assert output["loop_recovery"] == "repair_candidate_plan_file"
    assert "collaboration_summary must explain the governance story" in output["validation_error"]
    assert "spec must include at least one Success Surface bullet" in output["validation_error"]
    assert "spec Residual Risk guidance must name accepted risk handling or fail closed" in output["validation_error"]
    assert "rewrite collaboration_summary with the concrete task, evidence flow, blockers, and GateKeeper closure" in output["repair_focus"]
    assert "add # Success Surface bullets that make the task judgment reviewable and runnable" in output["repair_focus"]
    assert "add # Residual Risk guidance naming accepted risks, owners/follow-ups, or fail-closed conditions" in output["repair_focus"]

def test_cli_agent_loop_reports_candidate_repair_state_after_failed_gen(
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
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
            "Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
        ],
    )
    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir), "--no-web"])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert loop_result.exit_code == 1
    output_text = loop_result.output
    error_text = _error_text(loop_result)
    assert "loop_recovery: repair the current plan file before /loopora-run can start" in output_text
    assert error_text == ""
    assert "plan_file_to_repair:" in output_text
    assert "preview_plan_copy:" in output_text
    assert "repair_focus:" in output_text
    assert "preview_url: /loops/new/bundle?alignment_session_id=" in output_text
    assert "next_repair_step: repair the candidate plan file so it preserves repair_task_message and repair_focus" in output_text
    assert "project the task objects from --message" in output_text

def test_cli_agent_gen_with_candidate_not_fit_reports_reframe_before_loop(
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
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
            "There is no need for a Loopora loop here; just answer directly.",
            "--bundle-file",
            str(bundle_file),
            "--no-web",
        ],
    )
    loop_result = runner.invoke(cli.app, ["agent", "codex", "run", "--workdir", str(sample_workdir), "--no-web"])

    assert gen_result.exit_code == 0, gen_result.stdout
    assert "Loopora Loop preview needs plan file repair before /loopora-run" in gen_result.stdout
    assert "not_fit:" in gen_result.stdout
    assert "reframe the task with later evidence, handoff, or GateKeeper value" in gen_result.stdout
    assert "Loopora is not fit" in gen_result.stdout
    assert loop_result.exit_code == 1
    error_text = _error_text(loop_result)
    assert error_text == ""
    assert "loop_recovery: repair the current plan file before /loopora-run can start" in loop_result.output
    assert "not_fit:" in loop_result.output
    assert "one-off, direct-answer, no-new-evidence, or benchmark/test-harness-only" in loop_result.output
    assert "GateKeeper value" in loop_result.output
    assert "next_repair_step: repair the candidate plan file so it preserves repair_task_message and repair_focus" in loop_result.output

def test_cli_agent_gen_uses_repair_flag_when_candidate_status_is_not_failed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()

    class FakeService:
        def create_agent_bundle_candidate(self, request: AgentBundleCandidateRequest) -> dict:
            assert request.adapter == "codex"
            assert request.workdir == workdir
            assert request.message == "Repair this candidate without pretending it is runnable."
            return {
                "ready": False,
                "status": "blocked",
                "requires_web_alignment": False,
                "requires_candidate_repair": True,
                "session": {
                    "id": "session_repair",
                    "error_message": "candidate is missing required audit evidence",
                },
                "preview_path": "/loops/new/bundle?alignment_session_id=session_repair",
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "plan",
            "--workdir",
            str(workdir),
            "--message",
            "Repair this candidate without pretending it is runnable.",
            "--no-web",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "Loopora Loop preview needs plan file repair before /loopora-run" in result.stdout
    assert "needs candidate repair" not in result.stdout
    assert "validation_error: candidate is missing required audit evidence" in result.stdout
    assert "Loopora Loop preview status: blocked" not in result.stdout

def test_agent_bundle_candidate_rejects_task_context_mismatch(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_web_alignment"] is False
    assert generated["requires_candidate_repair"] is True
    assert generated["ready_candidate_sha256"] == ""
    assert generated["ready_candidate_bytes"] == 0
    assert generated["binding"]["requires_web_alignment"] is False
    assert generated["binding"]["requires_candidate_repair"] is True
    assert generated["binding"]["ready_candidate_sha256"] == ""
    assert generated["binding"]["ready_candidate_bytes"] == 0
    assert generated["session"].get("agent_entry_review", {}) == {}
    assert "host Agent task summary" in generated["session"]["error_message"]
    assert "refund" in generated["session"]["error_message"]
    assert "audit" in generated["session"]["error_message"]
    candidate_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_received"
    )
    assert candidate_event["payload"]["requires_candidate_repair"] is False
    assert candidate_event["payload"]["ready_candidate_sha256"] == ""
    assert candidate_event["payload"]["ready_candidate_bytes"] == 0
    assert any(
        event["event_type"] == "alignment_bundle_sync_failed"
        and "host Agent task summary" in event["payload"].get("error", "")
        for event in service.list_alignment_events(generated["session"]["id"])
    )

def test_agent_bundle_candidate_repair_session_keeps_web_plan_previewable(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Build a governed refund self-service flow with authorization, audit, and payment failure evidence.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["requires_candidate_repair"] is True
    client = TestClient(build_app(service=service))
    response = client.get(f"/api/alignments/sessions/{generated['session']['id']}/bundle")

    assert response.status_code == 200
    preview = response.json()
    assert preview["ok"] is True
    assert preview["session"]["status"] == "failed"
    assert preview["source_path"] == generated["session"]["bundle_path"]
    assert preview["validation"]["ok"] is False
    assert "host Agent task summary" in preview["validation"]["error"]
    assert preview["control_summary"]["coverage"]["target_count"] >= preview["control_summary"]["coverage"]["check_count"]
    assert preview["traceability"] == preview["control_summary"]["traceability"]

def test_agent_bundle_candidate_rejects_host_summary_that_says_loopora_not_fit(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir(exist_ok=True)
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir(exist_ok=True)
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Fix a README typo. One Agent pass plus one human review is enough, "
                "and later rounds will create no new evidence."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "Loopora is not fit" in generated["session"]["error_message"]
    assert any(
        event["event_type"] == "alignment_bundle_sync_failed"
        and "Loopora is not fit" in event["payload"].get("error", "")
        for event in service.list_alignment_events(generated["session"]["id"])
    )

def test_agent_bundle_candidate_rejects_chinese_host_summary_that_says_loopora_not_fit(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="修一个 README 错字。一次 Agent 执行加人工 review 已经足够，后续不会产生新证据。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_chinese_benchmark_only_host_summary(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="现有基准已经完全覆盖这次判断，直接跑基准就够了，不需要 Loopora。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_chinese_no_loop_host_summary(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="不用 Loopora，直接让 Agent 做完再人工看一眼就行。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_chinese_single_round_host_summary(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="这个任务跑一遍就行，不需要多轮，之后我人工确认即可。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]

@pytest.mark.parametrize(
    "message",
    [
        "这是一次性任务，不要长期循环。直接处理完即可。",
        "This is a one-off task; no Loopora loop is needed.",
        "There is no need for a Loopora loop here; just answer directly.",
        "A direct answer is enough; no future iteration will add proof.",
        "Just fix it once and I will review it manually.",
        "The stable proof harness already fully captures the judgment.",
        "现有契约测试已经完全覆盖这次判断，直接跑测试就够了。",
    ],
)
def test_agent_bundle_candidate_rejects_one_off_host_summary_variants(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    message: str,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=message,
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert generated["requires_candidate_repair"] is True
    assert generated["loopora_fit_contradiction"] is True
    assert generated["binding"]["loopora_fit_contradiction"] is True
    assert "Loopora is not fit" in generated["session"]["error_message"]
    candidate_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_received"
    )
    assert candidate_event["payload"]["loopora_fit_contradiction"] is True

def test_agent_bundle_candidate_rejects_governance_markers_without_runtime_responsibilities(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] += " AGENTS.md, design/README.md, design/, and tests/ are project-local governance markers."
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the focused starter experience while following AGENTS.md, design/README.md, design/, "
                "and tests/ as runtime governance inputs."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "project-local governance markers" in generated["session"]["error_message"]
    assert "Builder reading" in generated["session"]["error_message"]

def test_agent_bundle_candidate_uses_workdir_snapshot_for_governance_markers(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    (sample_workdir / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    (sample_workdir / "design").mkdir(exist_ok=True)
    (sample_workdir / "design" / "README.md").write_text("# Design\n", encoding="utf-8")
    (sample_workdir / "tests").mkdir(exist_ok=True)

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the focused starter experience in the target workdir with small, maintainable changes "
                "that preserve the primary user flow."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "project-local governance markers" in generated["session"]["error_message"]

def test_agent_bundle_candidate_uses_parent_agents_file_as_governance_marker(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    project = tmp_path / "project"
    workdir = project / "packages" / "app"
    workdir.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_text("Project rules.\n", encoding="utf-8")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=workdir,
            message=(
                "Build the focused starter experience in the target workdir with small, maintainable changes "
                "that preserve the primary user flow."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "project-local governance markers" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_governance_markers_as_role_responsibilities(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["builder"]["prompt_markdown"] += (
        "\n\nRead AGENTS.md, design/README.md, design/, and tests/ before changing code, "
        "and follow those project-local governance contracts in the Builder handoff."
    )
    role_by_key["contract-inspector"]["prompt_markdown"] += (
        "\n\nInspector must verify AGENTS.md, design/README.md, design/, and tests/ were followed, "
        "and must mark skipped local governance as weak or missing evidence."
    )
    role_by_key["gatekeeper"]["prompt_markdown"] += (
        "\n\nGateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ responsibilities "
        "as Weak, Unproven, or Blocking before accepting the run."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the focused starter experience while following AGENTS.md, design/README.md, design/, "
                "and tests/ as runtime governance inputs."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_residual_risk_policy_missing_owner_path(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Accept manual billing export as residual risk only when explicitly named; fail closed on unproven primary-flow behavior or weak verification evidence.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Accept manual billing export as a residual risk only when Support owns the follow-up; "
                "unverified primary flow must fail closed."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "residual-risk policy" in generated["session"]["error_message"]
    assert "owner/follow-up" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_chinese_residual_risk_missing_owner_path(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Accept manual billing export as residual risk only when explicitly named; fail closed on unproven primary-flow behavior or weak verification evidence.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="残余风险：手动账单导出只有客服负责人跟进工单时才可接受；未验证主流程必须失败关闭。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "residual-risk policy" in generated["session"]["error_message"]
    assert "owner/follow-up" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_residual_risk_policy_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        (
            "Accept manual billing export as residual risk only when Support owns the follow-up; "
            "fail closed on unproven primary-flow behavior or weak verification evidence."
        ),
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Confirm Support owns the manual billing export follow-up before accepting it as residual risk."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Accept manual billing export as a residual risk only when Support owns the follow-up; "
                "unverified primary flow must fail closed."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_no_accepted_residual_risk_policy_relaxed_in_bundle(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Accept unproven billing export as residual risk when explicitly named; fail closed on weak verification evidence.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="No residual risk is acceptable; unproven billing export must fail closed.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "residual-risk policy" in generated["session"]["error_message"]
    assert "no-accepted-residual-risk" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_explicit_success_criteria_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the refund approval path so Support admin can approve a refund and audit log records the actor.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Success means Support admin can approve a refund, audit log records the actor, "
                "and customer receives an email notification."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "success criteria" in generated["session"]["error_message"]
    assert "notification/message" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_chinese_success_criteria_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="成功标准：客服可以批准退款，审计日志记录操作者，并且客户收到通知邮件。",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "success criteria" in generated["session"]["error_message"]
    assert "notification/message" in generated["session"]["error_message"]
    assert "退款" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_explicit_success_criteria_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        (
            "Ship the refund approval path so Support admin can approve a refund, audit log records the actor, "
            "and the customer receives an email notification."
        ),
    )
    bundle["workflow"]["collaboration_intent"] += (
        " GateKeeper must verify the refund approval, audit log record, and customer email notification before finishing."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Success means Support admin can approve a refund, audit log records the actor, "
                "and customer receives an email notification."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_accessibility_and_locale_success_criteria_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Success means keyboard users can complete checkout, screen reader labels are available, "
                "and Chinese and English variants preserve the same action."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "success criteria" in generated["session"]["error_message"]
    assert "accessibility/a11y" in generated["session"]["error_message"]
    assert "locale/i18n" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_accessibility_and_locale_success_criteria_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        (
            "Ship the checkout path so keyboard users can complete checkout, screen reader labels are available, "
            "and Chinese and English variants preserve the same action."
        ),
    )
    bundle["workflow"]["collaboration_intent"] += (
        " Inspector verifies keyboard access, screen reader labels, and Chinese and English action parity before GateKeeper closes."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Success means keyboard users can complete checkout, screen reader labels are available, "
                "and Chinese and English variants preserve the same action."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_explicit_fake_done_risk_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the billing export in the target workdir with small, maintainable changes that preserve the primary user flow.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the billing export. Fake done is a CSV download that omits permission audit; "
                "do not pass until permission audit proof exists."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "fake-done risks" in generated["session"]["error_message"]
    assert "permission/audit" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_explicit_fake_done_risk_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the billing export in the target workdir with small, maintainable changes that preserve the primary user flow.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nFake Done: A CSV download that omits permission audit is not done; "
        "GateKeeper must block until permission audit proof exists."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Treat any billing CSV download without permission audit proof as fake done."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the billing export. Fake done is a CSV download that omits permission audit; "
                "do not pass until permission audit proof exists."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_payment_fake_done_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the refund payment path in the target workdir with small, maintainable changes.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the refund payment path. Fake done is marking refund success without "
                "payment-provider failure replay or billing ledger proof."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "fake-done risks" in generated["session"]["error_message"]
    assert "payment/refund/billing" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_payment_fake_done_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the refund payment path in the target workdir with small, maintainable changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nFake Done: Marking refund success without payment-provider failure replay "
        "or billing ledger proof is fake done."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Treat any refund success without payment failure replay and billing ledger proof as fake done."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the refund payment path. Fake done is marking refund success without "
                "payment-provider failure replay or billing ledger proof."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_accessibility_and_locale_fake_done_risk_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build checkout. Fake done is an English-only flow that looks complete but has no keyboard "
                "or screen reader proof."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "fake-done risks" in generated["session"]["error_message"]
    assert "accessibility/i18n" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_explicit_evidence_preferences_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the checkout instrumentation in the target workdir with small, maintainable changes.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build checkout instrumentation. Evidence must include a browser journey and audit log command output "
                "before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "evidence preferences" in generated["session"]["error_message"]
    assert "audit/log" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_explicit_evidence_preferences_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the checkout instrumentation in the target workdir with small, maintainable changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nEvidence Preference: Require a browser journey plus audit log command output before GateKeeper can pass."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["evidence-inspector"]["prompt_markdown"] += (
        "\n\nCollect browser journey evidence and audit log command output for checkout instrumentation."
    )
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Pass only with browser journey proof and audit log command evidence."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build checkout instrumentation. Evidence must include a browser journey and audit log command output "
                "before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_payment_evidence_preferences_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the refund payment flow. Evidence must include payment-provider failure replay "
                "and billing ledger command output before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "evidence preferences" in generated["session"]["error_message"]
    assert "payment/refund/billing" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_payment_evidence_preferences_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the refund payment flow in the target workdir with small, maintainable changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nEvidence Preference: Require payment-provider failure replay and billing ledger command output before GateKeeper can pass."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["evidence-inspector"]["prompt_markdown"] += (
        "\n\nCollect payment-provider failure replay evidence and billing ledger command output."
    )
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Pass only with payment failure replay proof and billing ledger evidence."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build the refund payment flow. Evidence must include payment-provider failure replay "
                "and billing ledger command output before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_accessibility_and_locale_evidence_preferences_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Build checkout. Evidence must include keyboard navigation proof, a screen reader label check, "
                "and Chinese and English locale verification before GateKeeper can pass."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "evidence preferences" in generated["session"]["error_message"]
    assert "accessibility/a11y" in generated["session"]["error_message"]
    assert "locale/i18n" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_explicit_tradeoff_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["collaboration_summary"] = bundle["collaboration_summary"].replace(
        "Prefer a smaller proven flow over polished but unproven breadth, and let GateKeeper reject speed or surface completeness when evidence is weak. ",
        "",
    )
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace("Accept minor polish gaps", "Accept minor follow-up gaps")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Prioritize proof over speed: block polished-looking fake completion until evidence proves "
                "the primary flow."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "judgment tradeoffs" in generated["session"]["error_message"]
    assert "speed/polish" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_explicit_tradeoff_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] += (
        "\n\nTradeoff: prioritize proof over speed; UI polish must wait until primary-flow evidence is Proven."
    )
    bundle["workflow"]["collaboration_intent"] += (
        " GateKeeper should block polished-looking fake completion when proof is weak."
    )
    role_by_key = {role["key"]: role for role in bundle["role_definitions"]}
    role_by_key["gatekeeper"]["posture_notes"] += (
        " Reject speed-first or polish-first closure unless direct evidence proves the primary flow."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Prioritize proof over speed: block polished-looking fake completion until evidence proves "
                "the primary flow."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_pragmatic_progress_tradeoff_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prefer strict blocking over pragmatic progress when evidence is weak.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "judgment tradeoffs" in generated["session"]["error_message"]
    assert "pragmatic/progress" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_pragmatic_progress_tradeoff_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] += "\n\nTradeoff: strict blocking beats pragmatic progress when evidence is weak."
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prefer strict blocking over pragmatic progress when evidence is weak.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"

def test_agent_bundle_candidate_rejects_explicit_execution_strategy_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the billing refund path in the target workdir with small, maintainable changes.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Ship the billing refund path. Execution strategy: first repair the root cause before "
                "expanding dashboards or polishing UI."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "execution strategy" in generated["session"]["error_message"]
    assert "repair/root-cause" in generated["session"]["error_message"]

def test_agent_bundle_candidate_rejects_labeled_single_execution_strategy_missing_from_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the billing refund path in the target workdir with small, maintainable changes.",
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the billing refund path. Execution strategy: first repair the root cause.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is False
    assert generated["status"] == "failed"
    assert "execution strategy" in generated["session"]["error_message"]
    assert "repair/root-cause" in generated["session"]["error_message"]

def test_agent_bundle_candidate_accepts_explicit_execution_strategy_in_runtime_surfaces(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle = yaml.safe_load(alignment_bundle_yaml(str(sample_workdir.resolve())))
    bundle["spec"]["markdown"] = bundle["spec"]["markdown"].replace(
        "Ship the focused starter experience in the target workdir with small, maintainable changes that preserve the primary user flow.",
        "Ship the billing refund path in the target workdir with small, maintainable changes.",
    )
    bundle["spec"]["markdown"] += (
        "\n\nExecution Strategy: first repair the root cause, then consider dashboard expansion or UI polish."
    )
    bundle["workflow"]["collaboration_intent"] += (
        " Builder should repair the root cause before any dashboard expansion or UI polish."
    )
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message=(
                "Ship the billing refund path. Execution strategy: first repair the root cause before "
                "expanding dashboards or polishing UI."
            ),
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"
