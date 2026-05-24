from __future__ import annotations

from agent_adapter_helpers import *

@pytest.mark.parametrize(
    "agent_case",
    [
        {
            "adapter": "claude",
            "entry_source": "claude_project_skill",
            "context_id": "claude-session-a",
            "context_source": "explicit",
        },
        {
            "adapter": "opencode",
            "entry_source": "opencode_project_command",
            "context_id": "",
            "context_source": "workdir",
        },
    ],
)
def test_peer_agent_gen_validates_ready_bundle_and_loop_starts_run(
    service_factory,
    monkeypatch,
    tmp_path: Path,
    sample_workdir: Path,
    agent_case: dict[str, str],
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-thread-must-not-bind-peer-agent")
    adapter = agent_case["adapter"]
    entry_source = agent_case["entry_source"]
    context_id = agent_case["context_id"]
    context_source = agent_case["context_source"]

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter=adapter,
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            context_id=context_id,
            entry_source=entry_source,
        )
    )

    assert generated["adapter"] == adapter
    assert generated["candidate_origin"] == "agent_entry"
    assert generated["candidate_entry_source"] == entry_source
    assert generated["host_context_id"] == context_id
    assert generated["ready"] is True
    assert generated["binding"]["context_source"] == context_source
    assert generated["binding"]["host_context_id"] == context_id
    assert generated["binding"]["candidate_origin"] == "agent_entry"
    assert generated["binding"]["candidate_adapter"] == adapter
    assert generated["binding"]["candidate_entry_source"] == entry_source
    assert generated["binding"]["entry_invocations"][-1]["entry_source"] == entry_source
    candidate_events = service.list_alignment_events(generated["session"]["id"], limit=20)
    assert any(
        event["event_type"] == "agent_candidate_received"
        and event["payload"]["candidate_origin"] == "agent_entry"
        and event["payload"]["adapter"] == adapter
        and event["payload"]["entry_source"] == entry_source
        and event["payload"]["host_context_id"] == context_id
        and event["payload"]["has_candidate_yaml"] is True
        for event in candidate_events
    )

    started = service.start_agent_loop(
        adapter,
        workdir=sample_workdir,
        context_id=context_id,
        entry_source=entry_source,
        execute_async=False,
    )

    assert started["adapter"] == adapter
    assert started["run"]["id"]
    assert started["started_new_run"] is True
    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    assert started["next_step"]["step_id"] == "builder_step"
    assert [item["action"] for item in started["binding"]["entry_invocations"][-2:]] == ["plan", "run"]
    assert {item["entry_source"] for item in started["binding"]["entry_invocations"][-2:]} == {entry_source}
    final = _drive_agent_native_run_to_success(
        service,
        adapter=adapter,
        started=started,
        workdir=sample_workdir,
        context_id=context_id,
    )
    assert final["complete"] is True

def test_codex_agent_binding_is_scoped_by_host_context(service_factory, tmp_path: Path, sample_workdir: Path) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Bind this READY bundle to one Codex thread.",
            bundle_file=bundle_file,
            context_id="thread-a",
        )
    )
    assert generated["host_context_id"] == "thread-a"
    assert generated["binding"]["host_context_id"] == "thread-a"

    with pytest.raises(LooporaConflictError, match="choose a recoverable context"):
        service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-b", execute_async=False)

    started = service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-a", execute_async=False)
    thread_b_resolution = service.resolve_loopora_context(
        sample_workdir,
        intent="run",
        adapter="codex",
        context_id="thread-b",
    )

    assert started["started_new_run"] is True
    assert started["binding"]["context_source"] == "explicit"
    assert started["binding"]["host_context_id"] == "thread-a"
    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    assert thread_b_resolution["action"] == "choose_recoverable_context"
    assert thread_b_resolution["requires_user_choice"] is True
    assert thread_b_resolution["confidence"] == "single_recoverable"
    assert thread_b_resolution["choices"][0]["linked_run_id"] == started["run"]["id"]

def test_agent_run_context_resolution_covers_empty_resume_and_ambiguous_recovery(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    empty = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-empty")
    assert empty["action"] == "plan_first"
    assert empty["confidence"] == "no_binding"
    assert empty["requires_user_choice"] is False

    bundle_a = tmp_path / "bundle-a.yml"
    bundle_a.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    generated_a = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Create the first recoverable Loop.",
            bundle_file=bundle_a,
            context_id="thread-a",
        )
    )
    exact_ready = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-a")
    assert exact_ready["action"] == "start_ready_preview"
    assert exact_ready["confidence"] == "exact_binding"
    assert exact_ready["choice"]["alignment_session_id"] == generated_a["session"]["id"]
    assert exact_ready["choice"]["action"] == "start_ready_preview"

    recover_ready = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")
    assert recover_ready["action"] == "choose_recoverable_context"
    assert recover_ready["confidence"] == "single_recoverable"
    assert recover_ready["choices"][0]["action"] == "start_ready_preview"
    assert recover_ready["choices"][0]["alignment_session_id"] == generated_a["session"]["id"]

    started_a = service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-a", execute_async=False)
    exact_active = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-a")
    resumed_a = service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-a", execute_async=False)
    assert exact_active["action"] == "resume_run"
    assert exact_active["confidence"] == "exact_binding"
    assert exact_active["choice"]["action"] == "resume_active_run"
    assert exact_active["choice"]["linked_run_id"] == started_a["run"]["id"]
    assert resumed_a["started_new_run"] is False
    assert resumed_a["run"]["id"] == started_a["run"]["id"]
    assert resumed_a["complete"] is False

    bundle_b = tmp_path / "bundle-b.yml"
    bundle_b.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    generated_b = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Create a second recoverable Loop.",
            bundle_file=bundle_b,
            context_id="thread-b",
        )
    )
    ambiguous = service.resolve_loopora_context(sample_workdir, intent="run", adapter="codex", context_id="thread-new")

    choices_by_session = _assert_ambiguous_agent_recovery_choices(
        ambiguous,
        generated_a=generated_a,
        generated_b=generated_b,
        started_a=started_a,
    )

    selected_a = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-new",
        source_option_id=choices_by_session[generated_a["session"]["id"]]["option_id"],
        execute_async=False,
    )
    assert selected_a["started_new_run"] is False
    assert selected_a["run"]["id"] == started_a["run"]["id"]
    assert selected_a["binding"]["selected_option_id"] == choices_by_session[generated_a["session"]["id"]]["option_id"]
    assert selected_a["binding"]["context_card"]["schema_version"] == 1
    assert selected_a["binding"]["context_card"]["entry_version"] == agent_adapters.ADAPTER_VERSION
    assert selected_a["binding"]["context_card"]["recovery_action"] == "resume_run"

def test_cli_agent_run_without_exact_binding_reports_recoverable_context(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            context_id="thread-original",
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-original",
        entry_source="codex_project_skill",
        execute_async=False,
    )
    monkeypatch.setattr(cli, "create_service", lambda: service)
    runner = CliRunner()

    json_result = runner.invoke(
        cli.app,
        ["agent", "codex", "run", "--workdir", str(sample_workdir), "--context-id", "thread-new", "--no-web", "--json"],
    )

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    payload_keys = list(payload)
    assert payload_keys.index("agent_loop_recovery_summary") < payload_keys.index("context_resolution")
    summary = payload["agent_loop_recovery_summary"]
    assert summary["loop_recovery"] == "choose_recoverable_context"
    _assert_codex_native_surface_summary(summary)
    assert summary["choice_count"] == 1
    assert summary["runnable_choice_count"] == 1
    assert summary["non_runnable_choice_count"] == 0
    assert "one runnable context is available" in summary["selection_hint"]
    assert summary["choices"][0]["choice_status"] == "active_run"
    assert summary["choices"][0]["choice_hint"].startswith("Continue the in-progress run")
    assert summary["choices"][0]["next_loop_command"].startswith("/loopora-run option:agent_run:")
    assert "--source-option-id agent_run:" in summary["choices"][0]["next_cli_command"]
    assert payload["loop_recovery"] == "choose_recoverable_context"
    assert payload["context_resolution"]["requires_user_choice"] is True
    assert payload["context_resolution"]["choice_count"] == 1
    assert payload["context_resolution"]["runnable_choice_count"] == 1
    assert payload["context_resolution"]["non_runnable_choice_count"] == 0
    assert "one runnable context is available" in payload["context_resolution"]["selection_hint"]
    assert payload["context_resolution"]["choices"][0]["linked_run_id"] == started["run"]["id"]
    _assert_recovery_choice_has_copyable_commands(payload["context_resolution"]["choices"][0])
    _assert_recovery_choice_has_status_hint(payload["context_resolution"]["choices"][0], expected_status="active_run")

    text_result = runner.invoke(
        cli.app,
        ["agent", "codex", "run", "--workdir", str(sample_workdir), "--context-id", "thread-new", "--no-web"],
    )

    assert text_result.exit_code == 1
    assert "loop_recovery: choose a recoverable Loopora context before /loopora-run can start" in text_result.stdout
    assert "context_choices: 1 total / 1 runnable / 0 non-runnable" in text_result.stdout
    assert "choice_status: active_run" in text_result.stdout
    assert "choice_hint: Continue the in-progress run" in text_result.stdout
    assert "runnable: true" in text_result.stdout
    assert "alignment_status: running_loop" in text_result.stdout
    assert "updated_at: " in text_result.stdout
    assert "next_loop_command: /loopora-run option:agent_run:" in text_result.stdout
    assert "next_cli_command: " in text_result.stdout
    assert "--source-option-id agent_run:" in text_result.stdout
    assert "for a runnable choice, paste one next_loop_command back to the Agent" in text_result.stdout

def test_cli_agent_next_without_exact_binding_reports_direct_run_recovery(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
    monkeypatch,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            context_id="thread-original",
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-original",
        entry_source="codex_project_skill",
        execute_async=False,
    )
    monkeypatch.setattr(cli, "create_service", lambda: service)
    runner = CliRunner()

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "next",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-new",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    payload_keys = list(payload)
    assert payload_keys.index("agent_next_recovery_summary") < payload_keys.index("context_resolution")
    summary = payload["agent_next_recovery_summary"]
    assert summary["loop_recovery"] == "choose_recoverable_context"
    _assert_codex_native_surface_summary(summary)
    assert summary["choice_count"] == 1
    assert summary["runnable_choice_count"] == 1
    assert summary["next_active_run_command"].endswith(f"--run-id {started['run']['id']} --json --entry-source codex_project_skill")
    assert summary["choices"][0]["choice_status"] == "active_run"
    assert summary["choices"][0]["next_agent_command"].endswith(
        f"--run-id {started['run']['id']} --json --entry-source codex_project_skill"
    )
    assert payload["loop_recovery"] == "choose_recoverable_context"
    assert payload["recovery_source"] == "agent_next_missing_binding"
    assert payload["context_resolution"]["choices"][0]["linked_run_id"] == started["run"]["id"]
    assert payload["context_resolution"]["choices"][0]["next_agent_command"].endswith(
        f"--run-id {started['run']['id']} --json --entry-source codex_project_skill"
    )

    text_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "next",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-new",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert text_result.exit_code == 1
    assert _error_text(text_result) == ""
    assert "loop_recovery: choose a recoverable Loopora context before claiming the next Agent step" in text_result.stdout
    _assert_labeled_loopora_agent_command(text_result.stdout, "next_active_run_command", "next")
    assert f"--run-id {started['run']['id']}" in text_result.stdout
    _assert_labeled_loopora_agent_command(text_result.stdout, "next_agent_command", "next")
    assert "for an already active run, run its next_agent_command to claim the current step" in text_result.stdout

def test_cli_agent_run_active_workdir_conflict_reports_recovery_commands(sample_workdir: Path, monkeypatch) -> None:
    loopora_home = sample_workdir.parent / "loopora home"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))

    class FakeService:
        def start_agent_loop(self, *_args, **_kwargs):
            raise LooporaConflictError(f"another active run is already using {sample_workdir.resolve()}")

        def get_runtime_activity(self):
            return {
                "runs": [
                    {
                        "id": "run_active",
                        "loop_id": "loop_refund",
                        "loop_name": "Refund safety Loop",
                        "status": "awaiting_agent",
                        "active_role": "",
                        "current_iter": 0,
                        "workdir": str(sample_workdir.resolve()),
                        "updated_at": "2026-05-19T20:51:26Z",
                    }
                ]
            }

        def run_observation_snapshot(self, run_id: str):
            assert run_id == "run_active"
            return {
                "current_agent_step": {
                    "step_id": "builder_step",
                    "target_agent": "loopora-builder",
                    "context_absolute_path": str(sample_workdir / ".loopora" / "runs" / "run_active" / "context.json"),
                    "submit_hint": {
                        "result_template_absolute_path": str(
                            sample_workdir / ".loopora" / "agent_outbox" / "codex" / "run_active__builder_step.result.template.json"
                        )
                    },
                }
            }

    monkeypatch.setattr(cli, "create_service", FakeService)
    runner = CliRunner()

    json_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-new",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert json_result.exit_code == 1
    assert _error_text(json_result) == ""
    payload = json.loads(json_result.stdout)
    payload_keys = list(payload)
    assert payload_keys.index("agent_loop_recovery_summary") < payload_keys.index("active_runs")
    summary = payload["agent_loop_recovery_summary"]
    assert summary["loop_recovery"] == "active_run_conflict"
    _assert_codex_native_surface_summary(summary)
    assert summary["active_run_count"] == 1
    assert summary["active_runs"][0]["id"] == "run_active"
    assert summary["active_runs"][0]["status"] == "awaiting_agent"
    assert summary["active_runs"][0]["loop_name"] == "Refund safety Loop"
    assert summary["active_runs"][0]["current_step"]["step_id"] == "builder_step"
    assert summary["active_runs"][0]["current_step"]["target_agent"] == "loopora-builder"
    assert summary["next_active_run_command"].endswith("--run-id run_active --json --entry-source codex_project_skill")
    _assert_loopora_cli_command(
        summary["next_active_run_command"],
        "loopora agent codex next",
        loopora_home=loopora_home,
    )
    _assert_loopora_cli_command(
        summary["stop_active_run_command"],
        "loopora loops stop run_active",
        loopora_home=loopora_home,
    )
    assert payload["loop_recovery"] == "active_run_conflict"
    assert payload["message"].endswith("before starting another preview or run")
    assert payload["active_runs"][0]["id"] == "run_active"
    assert payload["active_runs"][0]["current_step"]["step_id"] == "builder_step"
    assert payload["active_runs"][0]["current_step"]["target_agent"] == "loopora-builder"
    assert payload["next_active_run_command"].endswith("--run-id run_active --json --entry-source codex_project_skill")
    _assert_loopora_cli_command(
        payload["stop_active_run_command"],
        "loopora loops stop run_active",
        loopora_home=loopora_home,
    )

    text_result = runner.invoke(
        cli.app,
        [
            "agent",
            "codex",
            "run",
            "--workdir",
            str(sample_workdir),
            "--context-id",
            "thread-new",
            "--entry-source",
            "codex_project_skill",
            "--no-web",
        ],
    )

    assert text_result.exit_code == 1
    assert _error_text(text_result) == ""
    assert "loop_recovery: continue or stop the active Loopora run before starting another preview or run" in text_result.stdout
    assert "run_active status=awaiting_agent loop=Refund safety Loop step=builder_step target=loopora-builder" in text_result.stdout
    _assert_labeled_loopora_agent_command(text_result.stdout, "next_active_run_command", "next")
    stop_command = _labeled_value(text_result.stdout, "stop_active_run_command")
    _assert_loopora_cli_command(stop_command, "loopora loops stop run_active", loopora_home=loopora_home)

def test_cli_agent_run_reports_damaged_binding_recovery(service_factory, sample_workdir: Path, monkeypatch) -> None:
    service = service_factory(scenario="success")
    binding_path = agent_adapters.agent_context_binding_path("codex", sample_workdir, context_id="thread-broken")
    binding_path.parent.mkdir(parents=True)
    binding_path.write_text("{not-json", encoding="utf-8")
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
            "--context-id",
            "thread-broken",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["loop_recovery"] == "repair_agent_binding"
    assert "agent binding is unreadable" in payload["binding_error"]
    assert "loopora init codex --check" in payload["check_command"]

def test_agent_native_observation_snapshot_projects_current_handoff(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience with evidence gaps visible.",
            bundle_file=bundle_file,
            context_id="thread-handoff",
            entry_source="codex_project_skill",
        )
    )

    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-handoff",
        entry_source="codex_project_skill",
        execute_async=False,
    )
    snapshot = service.run_observation_snapshot(started["run"]["id"])

    assert started["next_step"]["known_evidence_count"] == 0
    assert started["next_step"]["known_evidence_ids"] == []
    current_step = snapshot["current_agent_step"]
    _assert_agent_native_observation_current_step(current_step)
    _assert_agent_native_observation_artifacts(service, current_step, started, sample_workdir)

def test_agent_native_role_dispatch_projects_target_agent_config_availability(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience with evidence gaps visible.",
            bundle_file=bundle_file,
            context_id="thread-dispatch-config",
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        context_id="thread-dispatch-config",
        entry_source="codex_project_skill",
        execute_async=False,
    )

    dispatch = started["next_step"]["role_dispatch"]
    config_path = Path(dispatch["target_agent_config_absolute_path"])
    assert dispatch["target_agent_config_exists"] is False

    state_path = Path(started["run"]["runs_dir"]) / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_step"]["capsule"]["submit_hint"]["command"] = "loopora agent codex submit --run-id stale --step-id builder_step"
    stale_coverage = {
        "status": "weak",
        "covered_check_count": 1,
        "missing_check_count": 1,
        "covered_check_ids": ["check_001"],
        "missing_check_ids": ["check_002"],
        "target_count": 9,
        "covered_target_count": 1,
        "weak_target_count": 0,
        "missing_target_count": 8,
        "blocked_target_count": 0,
        "top_gaps": [{"target_id": "done_when.check_002", "status": "missing"}],
    }
    state["active_step"]["capsule"]["required_coverage"] = dict(stale_coverage)
    state["active_step"]["context_packet"]["iteration"].update(
        {
            "coverage_status": stale_coverage["status"],
            "covered_check_count": stale_coverage["covered_check_count"],
            "missing_check_count": stale_coverage["missing_check_count"],
            "covered_check_ids": stale_coverage["covered_check_ids"],
            "missing_check_ids": stale_coverage["missing_check_ids"],
            "target_count": stale_coverage["target_count"],
            "covered_target_count": stale_coverage["covered_target_count"],
            "weak_target_count": stale_coverage["weak_target_count"],
            "missing_target_count": stale_coverage["missing_target_count"],
            "blocked_target_count": stale_coverage["blocked_target_count"],
            "coverage_top_gaps": stale_coverage["top_gaps"],
        }
    )
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text('name = "loopora-builder"\n', encoding="utf-8")
    refreshed = service.claim_agent_native_step(
        AgentNativeStepClaimRequest(
            adapter="codex",
            workdir=sample_workdir,
            context_id="thread-dispatch-config",
            run_id=started["run"]["id"],
            entry_source="codex_project_skill",
        )
    )
    snapshot = service.run_observation_snapshot(started["run"]["id"])

    assert refreshed["next_step"]["role_dispatch"]["target_agent_config_exists"] is True
    assert "--json" in refreshed["next_step"]["submit_hint"]["command"]
    assert refreshed["next_step"]["required_coverage"]["covered_check_count"] == 0
    assert refreshed["next_step"]["required_coverage"]["missing_check_count"] == 2
    assert refreshed["next_step"]["required_coverage"]["missing_check_ids"] == ["check_001", "check_002"]
    template_path = Path(refreshed["next_step"]["submit_hint"]["result_template_absolute_path"])
    template = json.loads(template_path.read_text(encoding="utf-8"))
    assert template["loopora_result_contract"]["required_coverage"]["covered_check_count"] == 0
    assert template["loopora_result_contract"]["required_coverage"]["missing_check_ids"] == ["check_001", "check_002"]
    assert snapshot["current_agent_step"]["target_agent_config_exists"] is True
    assert snapshot["current_agent_step"]["role_dispatch"]["target_agent_config_exists"] is True

def test_agent_native_takeaways_keep_active_iteration_open_after_role_handoff(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience with evidence gaps visible.",
            bundle_file=bundle_file,
            context_id="thread-active-takeaway",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, context_id="thread-active-takeaway", execute_async=False)
    builder_step = started["next_step"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            context_id="thread-active-takeaway",
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )
    snapshot = service.run_observation_snapshot(result["run"]["id"])
    iterations = snapshot["key_takeaways"]["iterations"]

    assert result["run"]["status"] == "awaiting_agent"
    assert result["submitted_step"]["step_id"] == "builder_step"
    assert result["submitted_step"]["evidence_refs"] == ["ev_000_00_builder_step"]
    assert result["submitted_step"]["summary"]
    assert Path(result["submitted_step"]["handoff_absolute_path"]).exists()
    assert result["next_step"]["step_id"] == "contract_inspection_step"
    assert len(iterations) == 1
    active_iteration = iterations[0]
    assert active_iteration["status"] == "running"
    assert active_iteration["summary"] == "Builder produced a structured handoff for downstream inspection."
    assert active_iteration["role_count"] == 1
    assert active_iteration["roles"][0]["status"] == "completed"
    assert active_iteration["coverage_status"] == "partial"
    assert active_iteration["missing_check_count"] == 2
    assert active_iteration["coverage_top_gaps"][0]["target_id"] == "done_when.check_001"

def test_agent_context_binding_path_hashes_untrusted_context_id(sample_workdir: Path) -> None:
    binding_path = agent_adapters.agent_context_binding_path(
        "codex",
        sample_workdir,
        context_id="../thread-a\nwith/slashes",
    )

    assert binding_path.parent.name == "bindings"
    assert binding_path.name.endswith(".json")
    assert "/" not in binding_path.stem
    assert ".." not in binding_path.stem
    assert "thread-a" not in binding_path.name

def test_agent_loop_rejects_binding_to_different_workdir_session(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    other_workdir = tmp_path / "other-project"
    other_workdir.mkdir()
    bundle_file = tmp_path / "other-bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(other_workdir.resolve())), encoding="utf-8")
    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=other_workdir,
            message="Bind this READY bundle to the other project only.",
            bundle_file=bundle_file,
        )
    )
    agent_adapters.write_agent_binding(
        "codex",
        sample_workdir,
        {
            "alignment_session_id": generated["session"]["id"],
            "alignment_status": "ready",
            "bundle_path": generated["session"]["bundle_path"],
            "preview_path": f"/loops/new/bundle?alignment_session_id={generated['session']['id']}",
        },
    )

    with pytest.raises(LooporaConflictError, match="different workdir"):
        service.start_agent_loop("codex", workdir=sample_workdir, execute_async=False)

@pytest.mark.parametrize("adapter", ["codex", "claude", "opencode"])
def test_cli_agent_loop_does_not_spawn_nested_worker_for_agent_native(adapter: str, monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    loopora_home = tmp_path / "loopora home"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    run_dir = tmp_path / "run"
    layout = RunArtifactLayout(run_dir)
    layout.initialize()
    _write_agent_native_cli_contract(layout)
    calls: dict[str, object] = {}

    class FakeService:
        def start_agent_loop(self, adapter: str, *, workdir: Path, context_id: str = "", entry_source: str = "", execute_async: bool = True):
            calls["adapter"] = adapter
            calls["workdir"] = workdir
            calls["context_id"] = context_id
            calls["entry_source"] = entry_source
            calls["execute_async"] = execute_async
            return {
                "execution_plane": "agent_native",
                "run": {
                    "id": "run_agent",
                    "status": "awaiting_agent",
                    "runs_dir": str(run_dir),
                    "workdir": str(workdir),
                },
                "run_path": "/runs/run_agent",
                "started_new_run": True,
                "next_step": {
                    "adapter": adapter,
                    "step_id": "builder_step",
                    "role": {"name": "Builder"},
                    "role_dispatch": {
                        "target_agent": "loopora-builder",
                        "target_agent_config_absolute_path": str(workdir / ".codex" / "agents" / "loopora-builder.toml"),
                        "target_agent_config_exists": False,
                    },
                    "action_policy": {"workspace": "workspace_write", "can_block": False, "can_finish_run": False},
                    "required_coverage": {
                        "status": "pending",
                        "covered_check_count": 0,
                        "missing_check_count": 2,
                        "top_gaps": [
                            {"target_id": "done_when.check_001", "text": "Support admin can approve a refund."},
                            {"target_id": "gatekeeper.finish", "text": "GateKeeper needs supporting evidence refs."},
                        ],
                    },
                    "continuation": {
                        "active": True,
                        "previous_run_id": "run_previous",
                        "previous_task_verdict": {"status": "insufficient_evidence"},
                        "coverage": {"covered_check_count": 1, "missing_check_count": 2},
                        "next_focus": ["done_when.check_001: Support admin path still lacks direct proof."],
                    },
                    "known_evidence_count": 3,
                    "context_absolute_path": str(run_dir / "iterations" / "iter_000" / "steps" / "00__builder_step" / "input.context.json"),
                    "capsule_absolute_path": str(run_dir / "iterations" / "iter_000" / "steps" / "00__builder_step" / "capsule.json"),
                    "submit_hint": {
                        "command": "loopora agent codex submit --run-id run_agent --step-id builder_step",
                        "result_file_contract": "Write one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit.",
                        "result_template_absolute_path": str(
                            workdir / ".loopora" / "agent_outbox" / "codex" / "run_agent__builder_step.result.template.json"
                        ),
                        "result_outbox_absolute_dir": str(workdir / ".loopora" / "agent_outbox" / "codex"),
                    },
                },
            }

    monkeypatch.setattr(cli, "create_service", FakeService)

    def fake_spawn_background_worker(_service, run: dict) -> dict:
        raise AssertionError(f"agent-native loop must not spawn a nested worker for {run['id']}")

    monkeypatch.setattr(cli, "_spawn_background_worker", fake_spawn_background_worker)
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        ["agent", adapter, "run", "--workdir", str(workdir), "--context-id", "thread-1", "--no-web"],
    )

    assert result.exit_code == 0, result.stdout
    assert calls["adapter"] == adapter
    assert calls["workdir"] == workdir
    assert calls["context_id"] == "thread-1"
    assert calls["entry_source"] == ""
    assert calls["execute_async"] is False
    _assert_agent_native_cli_output(result.stdout, layout, adapter=adapter, loopora_home=loopora_home)

    json_result = runner.invoke(
        cli.app,
        ["agent", adapter, "run", "--workdir", str(workdir), "--context-id", "thread-1", "--no-web", "--json"],
    )

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    _assert_agent_run_json_summary_reports_missing_dispatch(
        payload,
        adapter=adapter,
        workdir=workdir,
        loopora_home=loopora_home,
    )
    summary = payload["agent_run_summary"]
    continuation_summary = _assert_agent_run_summary_continuation(
        summary,
        previous_run_id="run_previous",
        previous_task_verdict_status="insufficient_evidence",
        missing_required_check_count=2,
    )
    assert continuation_summary["next_focus"] == ["done_when.check_001: Support admin path still lacks direct proof."]
