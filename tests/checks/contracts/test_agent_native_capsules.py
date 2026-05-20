from __future__ import annotations

from agent_adapter_helpers import *

def test_cli_claude_gen_accepts_ready_bundle_without_starting_run(tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "claude",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--bundle-file",
            str(bundle_file),
            "--context-id",
            "claude-session-a",
            "--entry-source",
            "claude_project_skill",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["adapter"] == "claude"
    assert payload["candidate_origin"] == "agent_entry"
    assert payload["candidate_entry_source"] == "claude_project_skill"
    assert payload["ready"] is True
    assert payload["status"] == "ready"
    assert payload["host_context_id"] == "claude-session-a"
    assert payload["binding"]["context_source"] == "explicit"
    assert payload["binding"]["host_context_id"] == "claude-session-a"
    assert payload["binding"]["candidate_origin"] == "agent_entry"
    assert payload["binding"]["candidate_adapter"] == "claude"
    assert payload["binding"]["candidate_entry_source"] == "claude_project_skill"
    assert payload["binding"]["entry_invocations"][-1]["entry_source"] == "claude_project_skill"
    assert payload["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert "run" not in payload

def test_agent_loop_after_web_imported_candidate_still_uses_agent_native(
    service_factory,
    monkeypatch,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_text = alignment_bundle_yaml(str(sample_workdir.resolve()))
    expected_sha, expected_bytes = _candidate_digest(bundle_text)
    expected_ready_sha, expected_ready_bytes = _ready_candidate_digest(bundle_text)
    bundle_file.write_text(bundle_text, encoding="utf-8")

    generated = service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Prepare a governed implementation loop.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    assert generated["candidate_sha256"] == expected_sha
    assert generated["candidate_bytes"] == expected_bytes
    assert generated["ready_candidate_sha256"] == expected_ready_sha
    assert generated["ready_candidate_bytes"] == expected_ready_bytes
    assert generated["binding"]["ready_candidate_sha256"] == expected_ready_sha
    assert generated["binding"]["ready_candidate_bytes"] == expected_ready_bytes
    assert generated["session"]["agent_entry_launch"]["ready_candidate_sha256"] == expected_ready_sha
    assert generated["session"]["agent_entry_launch"]["ready_candidate_bytes"] == expected_ready_bytes
    candidate_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_received"
    )
    assert candidate_event["payload"]["candidate_sha256"] == expected_sha
    assert candidate_event["payload"]["candidate_bytes"] == expected_bytes
    ready_event = next(
        event for event in service.list_alignment_events(generated["session"]["id"]) if event["event_type"] == "agent_candidate_ready_content"
    )
    assert ready_event["payload"]["candidate_sha256"] == expected_sha
    assert ready_event["payload"]["candidate_bytes"] == expected_bytes
    assert ready_event["payload"]["ready_candidate_sha256"] == expected_ready_sha
    assert ready_event["payload"]["ready_candidate_bytes"] == expected_ready_bytes
    ready_path = Path(generated["session"]["bundle_path"])
    ready_bundle = yaml.safe_load(ready_path.read_text(encoding="utf-8"))
    ready_bundle["metadata"]["description"] = "Imported from the current reviewed file after a valid local edit."
    ready_path.write_text(yaml.safe_dump(ready_bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")
    expected_import_sha, expected_import_bytes = _ready_candidate_digest(ready_path.read_text(encoding="utf-8"))
    assert expected_import_sha != expected_ready_sha
    imported = service.import_alignment_bundle(generated["session"]["id"], start_immediately=False)
    assert imported["session"]["status"] == "imported"
    assert imported["session"]["linked_loop_id"]
    assert not imported["session"].get("linked_run_id")

    def fail_nested_worker(run_id: str) -> None:
        raise AssertionError(f"Agent-first imported sessions must not start a headless worker for {run_id}")

    monkeypatch.setattr(service, "start_run_async", fail_nested_worker)

    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        entry_source="codex_project_skill",
        execute_async=True,
    )

    assert started["execution_plane"] == "agent_native"
    assert started["started_new_run"] is True
    assert started["run"]["status"] == "awaiting_agent"
    assert started["binding"]["execution_plane"] == "agent_native"
    assert started["binding"]["linked_run_id"] == started["run"]["id"]
    assert started["binding"]["ready_candidate_sha256"] == expected_import_sha
    assert started["binding"]["ready_candidate_bytes"] == expected_import_bytes
    assert started["next_step"]["execution_plane"] == "agent_native"

def test_web_import_cannot_headless_start_agent_first_preview(
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
            message="Prepare a governed implementation loop.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    with pytest.raises(LooporaConflictError, match="agent-first Loop previews must be started from /loopora-run"):
        service.import_alignment_bundle(generated["session"]["id"], start_immediately=True, execute_async=True)

    blocked_session = service.get_alignment_session(generated["session"]["id"])
    assert blocked_session["status"] == "ready"
    assert not blocked_session.get("linked_run_id")
    assert service.list_bundles() == []

    started = service.start_agent_loop(
        "codex",
        workdir=sample_workdir,
        entry_source="codex_project_skill",
        execute_async=True,
    )

    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    assert started["next_step"]["execution_plane"] == "agent_native"
    assert (Path(started["run"]["runs_dir"]) / "agent_native" / "state.json").exists()

def test_cli_agent_runtime_accepts_managed_entry_source_from_env(monkeypatch, tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    monkeypatch.setenv("LOOPORA_AGENT_ENTRY_SOURCE", "claude_project_skill")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "claude",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--bundle-file",
            str(bundle_file),
            "--context-id",
            "claude-session-a",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["binding"]["entry_invocations"][-1]["entry_source"] == "claude_project_skill"

def test_cli_opencode_gen_accepts_ready_bundle_without_starting_run(monkeypatch, tmp_path: Path, sample_workdir: Path) -> None:
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(alignment_bundle_yaml(str(sample_workdir.resolve())), encoding="utf-8")
    monkeypatch.setenv("CODEX_SESSION_ID", "codex-thread-must-not-bind-opencode")
    runner = CliRunner()

    result = runner.invoke(
        cli.app,
        [
            "agent",
            "opencode",
            "plan",
            "--workdir",
            str(sample_workdir),
            "--message",
            "Prepare a governed implementation loop.",
            "--bundle-file",
            str(bundle_file),
            "--entry-source",
            "opencode_project_command",
            "--no-web",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["adapter"] == "opencode"
    assert payload["candidate_origin"] == "agent_entry"
    assert payload["candidate_entry_source"] == "opencode_project_command"
    assert payload["ready"] is True
    assert payload["status"] == "ready"
    assert payload["host_context_id"] == ""
    assert payload["binding"]["context_source"] == "workdir"
    assert payload["binding"]["host_context_id"] == ""
    assert payload["binding"]["candidate_origin"] == "agent_entry"
    assert payload["binding"]["candidate_adapter"] == "opencode"
    assert payload["binding"]["candidate_entry_source"] == "opencode_project_command"
    assert payload["binding"]["entry_invocations"][-1]["entry_source"] == "opencode_project_command"
    assert payload["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert "run" not in payload

def test_codex_adapter_install_does_not_touch_user_configuration(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()
    agents = workdir / "AGENTS.md"
    codex_config = workdir / ".codex" / "config.toml"
    codex_config.parent.mkdir()
    agents.write_text("# User project rules\n", encoding="utf-8")
    codex_config.write_text("model = \"user-choice\"\n", encoding="utf-8")

    service.install_agent_adapter("codex", workdir=workdir)
    service.uninstall_agent_adapter("codex", workdir=workdir)

    assert agents.read_text(encoding="utf-8") == "# User project rules\n"
    assert codex_config.read_text(encoding="utf-8") == "model = \"user-choice\"\n"

def test_codex_adapter_refuses_unowned_target_files(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    custom_skill = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    custom_skill.parent.mkdir(parents=True)
    custom_skill.write_text("# User-owned skill\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError):
        service.install_agent_adapter("codex", workdir=workdir)

    assert custom_skill.read_text(encoding="utf-8") == "# User-owned skill\n"

def test_claude_adapter_refuses_unowned_target_files(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    custom_skill = workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md"
    custom_skill.parent.mkdir(parents=True)
    custom_skill.write_text("# User-owned Claude skill\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError):
        service.install_agent_adapter("claude", workdir=workdir)

    assert custom_skill.read_text(encoding="utf-8") == "# User-owned Claude skill\n"

def test_opencode_adapter_refuses_unowned_target_files(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    custom_command = workdir / ".opencode" / "commands" / "loopora-plan.md"
    custom_command.parent.mkdir(parents=True)
    custom_command.write_text("# User-owned OpenCode command\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError):
        service.install_agent_adapter("opencode", workdir=workdir)

    assert custom_command.read_text(encoding="utf-8") == "# User-owned OpenCode command\n"

def test_codex_adapter_status_reports_needs_update_for_managed_drift(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("codex", workdir=workdir)
    skill_path = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\n<!-- locally stale managed file -->\n", encoding="utf-8")

    status = service.get_agent_adapter("codex", workdir=workdir)

    assert status["status"] == "needs_update"
    assert any(item["path"].endswith("loopora-plan/SKILL.md") and item["state"] == "needs_update" for item in status["managed_files"])

def test_codex_adapter_status_reports_error_for_manifest_tracked_user_edit_without_marker(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("codex", workdir=workdir)
    skill_path = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    skill_path.write_text("# User edited this file after install\n", encoding="utf-8")

    status = service.get_agent_adapter("codex", workdir=workdir)

    assert status["status"] == "error"
    assert "loopora-plan/SKILL.md" in status["error"]
    with pytest.raises(LooporaConflictError):
        service.install_agent_adapter("codex", workdir=workdir)
    assert skill_path.read_text(encoding="utf-8") == "# User edited this file after install\n"

def test_claude_adapter_status_reports_needs_update_for_managed_drift(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("claude", workdir=workdir)
    skill_path = workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\n<!-- locally stale managed file -->\n", encoding="utf-8")

    status = service.get_agent_adapter("claude", workdir=workdir)

    assert status["status"] == "needs_update"
    assert any(item["path"].endswith("loopora-plan/SKILL.md") and item["state"] == "needs_update" for item in status["managed_files"])

def test_claude_adapter_status_reports_needs_update_for_missing_managed_session_hook(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("claude", workdir=workdir)
    settings_path = workdir / ".claude" / "settings.json"
    settings_path.write_text(json.dumps({"permissions": {"allow": []}}) + "\n", encoding="utf-8")

    status = service.get_agent_adapter("claude", workdir=workdir)

    assert status["status"] == "needs_update"
    assert any(item["path"] == ".claude/settings.json#hooks.SessionStart.loopora" and item["state"] == "missing" for item in status["managed_files"])

def test_opencode_adapter_status_reports_needs_update_for_managed_drift(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("opencode", workdir=workdir)
    command_path = workdir / ".opencode" / "commands" / "loopora-plan.md"
    command_path.write_text(command_path.read_text(encoding="utf-8") + "\n<!-- locally stale managed file -->\n", encoding="utf-8")

    status = service.get_agent_adapter("opencode", workdir=workdir)

    assert status["status"] == "needs_update"
    assert any(item["path"].endswith("loopora-plan.md") and item["state"] == "needs_update" for item in status["managed_files"])

def test_codex_agent_gen_validates_ready_bundle_and_loop_starts_run(
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
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )

    assert generated["ready"] is True
    assert generated["status"] == "ready"
    assert generated["preview_path"].startswith("/loops/new/bundle?alignment_session_id=")
    assert generated["binding"]["entry_invocations"][-1]["action"] == "plan"
    assert generated["binding"]["entry_invocations"][-1]["entry_source"] == "codex_project_skill"

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["run"]["id"]
    assert started["run_path"] == f"/runs/{started['run']['id']}"
    assert started["started_new_run"] is True
    assert started["execution_plane"] == "agent_native"
    assert started["run"]["status"] == "awaiting_agent"
    _assert_agent_run_summary_for_started_run(started)
    assert started["next_step"]["step_id"] == "builder_step"
    assert started["judgment_contract"]["contract_path"] == "contract/run_contract.json"
    assert "Prefer a smaller proven flow" in started["judgment_contract"]["collaboration_summary"]
    assert started["judgment_contract"]["judgment_tradeoffs"]
    assert started["judgment_contract"]["execution_strategy"]
    assert started["judgment_contract"]["local_governance"]
    assert started["judgment_contract"]["role_postures"]
    assert started["judgment_contract"]["completion_mode"] == "gatekeeper"
    assert any(target["id"] == "done_when.check_001" for target in started["judgment_contract"]["coverage_targets"])
    source_bundle = started["judgment_contract"]["source_bundle"]
    exported_bundle_yaml = service.export_bundle_yaml(started["binding"]["linked_bundle_id"])
    exported_bundle_data = exported_bundle_yaml.encode("utf-8")
    assert source_bundle["id"] == started["binding"]["linked_bundle_id"]
    assert source_bundle["bundle_sha256"] == hashlib.sha256(exported_bundle_data).hexdigest()
    assert source_bundle["bundle_bytes"] == len(exported_bundle_data)
    assert Path(source_bundle["bundle_yaml_path"]).exists()
    next_step_prompt = started["next_step"]["prompt"]
    assert "Bundle collaboration summary:" in next_step_prompt
    assert "Prefer a smaller proven flow over polished but unproven breadth" in next_step_prompt
    assert "Execution strategy:" in next_step_prompt
    assert "Local governance:" in next_step_prompt
    assert "Role postures:" in next_step_prompt
    assert "GateKeeper treats skipped local governance" in next_step_prompt
    assert "run-local: contract/run_contract.json" in next_step_prompt
    assert Path(started["next_step"]["context_absolute_path"]).exists()
    assert started["session"]["status"] == "running_loop"
    assert [item["action"] for item in started["binding"]["entry_invocations"][-2:]] == ["plan", "run"]
    assert {item["entry_source"] for item in started["binding"]["entry_invocations"][-2:]} == {"codex_project_skill"}
    final = _drive_agent_native_run_to_success(service, adapter="codex", started=started, workdir=sample_workdir)
    assert final["complete"] is True

def test_agent_run_summary_exposes_dispatch_next_when_role_agent_is_available() -> None:
    result = {
        "run": {"id": "run_dispatch", "status": "awaiting_agent"},
        "started_new_run": True,
        "complete": False,
        "next_step": {
            "step_id": "builder_step",
            "role": {"name": "Builder"},
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "target_agent_config_path": ".codex/agents/loopora-builder.toml",
                "target_agent_config_exists": True,
            },
        },
    }

    cli_agent_adapter_commands._attach_agent_run_dispatch_summary(result)

    summary = result["agent_run_summary"]
    assert summary["dispatch_next"] == (
        "invoke loopora-builder with the next context/capsule paths below; do not perform this role inline"
    )
    assert summary["next_step"]["dispatch_next"] == summary["dispatch_next"]

def test_agent_native_step_capsule_projects_full_judgment_contract(
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
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    step_judgment_contract = started["next_step"]["judgment_contract"]
    context_contract = json.loads(Path(started["next_step"]["context_absolute_path"]).read_text(encoding="utf-8"))["contract"]
    snapshot_contract = service.run_observation_snapshot(started["run"]["id"])["key_takeaways"]["judgment_contract"]

    assert step_judgment_contract["contract_path"] == started["judgment_contract"]["contract_path"]
    assert snapshot_contract["contract_path"] == started["judgment_contract"]["contract_path"]
    assert snapshot_contract["loop_fit_reasons"] == started["judgment_contract"]["loop_fit_reasons"]
    assert snapshot_contract["execution_strategy"] == started["judgment_contract"]["execution_strategy"]
    assert snapshot_contract["local_governance"] == started["judgment_contract"]["local_governance"]
    assert snapshot_contract["role_postures"] == started["judgment_contract"]["role_postures"]
    assert step_judgment_contract["collaboration_summary"].startswith(
        started["judgment_contract"]["collaboration_summary"].removesuffix("…")
    )
    assert step_judgment_contract["contract_path"] == context_contract["path"]
    assert step_judgment_contract["collaboration_summary"] == context_contract["collaboration_summary"]
    assert step_judgment_contract["loop_fit_reasons"] == context_contract["loop_fit_reasons"]
    assert step_judgment_contract["judgment_tradeoffs"] == context_contract["judgment_tradeoffs"]
    assert step_judgment_contract["execution_strategy"] == context_contract["execution_strategy"]
    assert step_judgment_contract["local_governance"] == context_contract["local_governance"]
    assert step_judgment_contract["role_postures"]
    assert context_contract["role_postures"]
    assert any("Keep implementation narrow" in item for item in step_judgment_contract["role_postures"])
    assert any(item["posture_notes"].startswith("Keep implementation narrow") for item in context_contract["role_postures"])
    assert step_judgment_contract["coverage_targets"] == context_contract["coverage_targets"]
    assert step_judgment_contract["success_surface"] == context_contract["success_surface"]
    assert step_judgment_contract["fake_done_states"] == context_contract["fake_done_states"]
    assert step_judgment_contract["evidence_preferences"] == context_contract["evidence_preferences"]
    assert step_judgment_contract["residual_risk"] == context_contract["residual_risk"]
    assert step_judgment_contract["completion_mode"] == context_contract["completion_mode"]

    state_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_step"]["capsule"].pop("judgment_contract", None)
    for field, replacement in {
        "judgment_tradeoffs": [],
        "execution_strategy": [],
        "local_governance": [],
        "success_surface": [],
        "fake_done_states": [],
        "evidence_preferences": [],
        "residual_risk": "",
    }.items():
        state["active_step"]["context_packet"]["contract"][field] = replacement
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    claimed = service.claim_agent_native_step(
        AgentNativeStepClaimRequest(adapter="codex", workdir=sample_workdir, run_id=started["run"]["id"])
    )
    assert claimed["next_step"]["judgment_contract"]["contract_path"] == claimed["judgment_contract"]["contract_path"]
    for field in (
        "judgment_tradeoffs",
        "execution_strategy",
        "local_governance",
        "success_surface",
        "fake_done_states",
        "evidence_preferences",
        "residual_risk",
    ):
        assert claimed["next_step"]["judgment_contract"][field] == started["judgment_contract"][field]
    assert claimed["next_step"]["judgment_contract"]["coverage_targets"] == context_contract["coverage_targets"]
    persisted_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted_state["active_step"]["capsule"]["judgment_contract"] == claimed["next_step"]["judgment_contract"]

def test_agent_native_required_coverage_refs_stay_known_when_evidence_query_filters_items(
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
            message="Keep blocked coverage evidence citable by the next Agent-native role.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )
    contract_step = result["next_step"]
    builder_evidence_id = contract_step["known_evidence_ids"][0]
    blocking_output = {
        "execution_summary": {"total_checks": 1, "passed": 0, "failed": 1, "errored": 0, "total_duration_ms": 1},
        "check_results": [
            {
                "id": "check_001",
                "title": "Primary contract proof",
                "status": "failed",
                "notes": "The Builder evidence does not prove the first required target.",
            }
        ],
        "dynamic_checks": [],
        "tester_observations": "Contract Inspector blocks the first required target using the Builder evidence.",
        "coverage_results": [
            {
                "target_id": "done_when.check_001",
                "status": "blocked",
                "evidence_refs": [builder_evidence_id],
                "note": "Builder evidence is insufficient for the first required target.",
            }
        ],
    }

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(contract_step["run_id"]),
            step_id=str(contract_step["step_id"]),
            output=blocking_output,
            host_dispatch=_agent_native_host_dispatch("codex", contract_step),
            entry_source="codex_project_skill",
        )
    )

    evidence_step = result["next_step"]
    blocking_evidence_id = "ev_000_01_contract_inspection_step"
    assert evidence_step["step_id"] == "evidence_inspection_step"
    assert evidence_step["required_coverage"]["top_gaps"][0]["evidence_refs"] == [blocking_evidence_id]
    assert blocking_evidence_id in evidence_step["known_evidence_ids"]
    known_evidence_refs = {item["id"]: item for item in evidence_step["known_evidence_refs"]}
    assert known_evidence_refs[builder_evidence_id]["claim"]
    assert known_evidence_refs[blocking_evidence_id]["claim"] == "Contract Inspector blocks the first required target using the Builder evidence."
    assert known_evidence_refs[blocking_evidence_id]["coverage_target_ids"] == ["done_when.check_001"]
    assert known_evidence_refs[blocking_evidence_id]["gatekeeper_support"] == "non_supporting"
    assert known_evidence_refs[blocking_evidence_id]["gatekeeper_support_reason"] == "result is blocked"
    assert evidence_step["required_coverage"]["target_count"] >= evidence_step["required_coverage"]["covered_check_count"]
    assert "blocked_target_count" in evidence_step["required_coverage"]

    context_packet = json.loads(Path(evidence_step["context_absolute_path"]).read_text(encoding="utf-8"))
    assert context_packet["iteration"]["target_count"] == evidence_step["required_coverage"]["target_count"]
    assert blocking_evidence_id in context_packet["evidence"]["known_ids"]
    assert any(item["id"] == blocking_evidence_id for item in context_packet["evidence"]["items"])

    template = json.loads(Path(evidence_step["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    assert blocking_evidence_id in template["loopora_result_contract"]["known_evidence_ids"]
    template_refs = {item["id"]: item for item in template["loopora_result_contract"]["known_evidence_refs"]}
    assert template_refs[blocking_evidence_id]["role_name"] == "Contract Inspector"
    assert template_refs[blocking_evidence_id]["coverage_target_ids"] == ["done_when.check_001"]
    assert template_refs[blocking_evidence_id]["gatekeeper_support"] == "non_supporting"

def test_agent_native_known_evidence_refs_classify_gatekeeper_support(
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
            message="Show which evidence refs can support GateKeeper.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    proof_path = sample_workdir / "proof" / "primary-flow.txt"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    proof_path.write_text("PASS: primary flow proof is project-owned.\n", encoding="utf-8")
    builder_output = _agent_native_step_output(builder_step)
    builder_output["changed_files"] = ["proof/primary-flow.txt"]
    builder_output["proof_files"] = ["proof/primary-flow.txt"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=builder_output,
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )

    contract_step = result["next_step"]
    builder_evidence_id = contract_step["known_evidence_ids"][0]
    step_refs = {item["id"]: item for item in contract_step["known_evidence_refs"]}
    assert step_refs[builder_evidence_id]["gatekeeper_support"] == "supporting"
    assert "proof-file" in step_refs[builder_evidence_id]["gatekeeper_support_reason"]
    assert step_refs[builder_evidence_id]["artifact_refs"] == [
        {"path": "proof/primary-flow.txt", "label": "proof-file:proof/primary-flow.txt"}
    ]

    template = json.loads(Path(contract_step["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    template_refs = {item["id"]: item for item in template["loopora_result_contract"]["known_evidence_refs"]}
    assert template_refs[builder_evidence_id]["gatekeeper_support"] == "supporting"
    assert "proof-file" in template_refs[builder_evidence_id]["gatekeeper_support_reason"]
    assert template_refs[builder_evidence_id]["artifact_refs"] == [
        {"path": "proof/primary-flow.txt", "label": "proof-file:proof/primary-flow.txt"}
    ]

def test_agent_native_duplicate_submit_cannot_append_second_evidence_entry(
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
            message="Keep agent-native step submission single-accept.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    state_path = layout.run_dir / "agent_native" / "state.json"
    stale_claimed_state = json.loads(state_path.read_text(encoding="utf-8"))

    first_result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )
    assert first_result["submitted_step"]["evidence_refs"] == ["ev_000_00_builder_step"]

    state_path.write_text(json.dumps(stale_claimed_state, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(LooporaConflictError, match="already submitted"):
        service.submit_agent_native_step(
            AgentNativeStepSubmitRequest(
                adapter="codex",
                workdir=sample_workdir,
                run_id=str(builder_step["run_id"]),
                step_id=str(builder_step["step_id"]),
                output=_agent_native_step_output(builder_step),
                host_dispatch=_agent_native_host_dispatch("codex", builder_step),
                entry_source="codex_project_skill",
            )
        )

    evidence_ids = [str(item.get("id") or "") for item in read_jsonl(layout.evidence_ledger_path)]
    assert evidence_ids.count("ev_000_00_builder_step") == 1

def test_agent_native_known_evidence_ids_dedupe_duplicate_ledger_entries(
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
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = started["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )
    layout = RunArtifactLayout(Path(started["run"]["runs_dir"]))
    builder_evidence = next(item for item in read_jsonl(layout.evidence_ledger_path) if item.get("id") == "ev_000_00_builder_step")
    append_jsonl(layout.evidence_ledger_path, builder_evidence)

    inspector_step = result["next_step"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(inspector_step["run_id"]),
            step_id=str(inspector_step["step_id"]),
            output=_agent_native_step_output(inspector_step),
            host_dispatch=_agent_native_host_dispatch("codex", inspector_step),
            entry_source="codex_project_skill",
        )
    )

    known_ids = result["next_step"]["known_evidence_ids"]
    assert known_ids == list(dict.fromkeys(known_ids))
    context_packet = json.loads(Path(result["next_step"]["context_absolute_path"]).read_text(encoding="utf-8"))
    assert context_packet["evidence"]["known_ids"] == list(dict.fromkeys(context_packet["evidence"]["known_ids"]))
    template = json.loads(Path(result["next_step"]["submit_hint"]["result_template_absolute_path"]).read_text(encoding="utf-8"))
    template_known_ids = template["loopora_result_contract"]["known_evidence_ids"]
    assert template_known_ids == list(dict.fromkeys(template_known_ids))

def test_agent_native_capsule_judgment_contract_falls_back_when_context_is_trimmed(tmp_path: Path) -> None:
    layout = RunArtifactLayout(tmp_path / "runs" / "run_capsule_fallback")
    layout.initialize()
    layout.run_contract_path.write_text(
        json.dumps(
            {
                "collaboration_summary": "Keep frozen judgment stronger than stale context.",
                "loop_fit_reasons": ["Later role handoffs need the same proof bar."],
                "judgment_tradeoffs": ["Evidence beats fast closure."],
                "execution_strategy": ["Prove inherited governance before polishing."],
                "local_governance": ["GateKeeper treats skipped AGENTS.md checks as Blocking."],
                "success_surface": ["Admin can complete the audited action."],
                "fake_done_states": ["Summary-only evidence is fake done."],
                "evidence_preferences": ["Require command output and audit artifacts."],
                "residual_risk": "No unmanaged residual risk is acceptable.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    contract = ServiceAgentNativeMixin._agent_native_capsule_judgment_contract(
        {"runs_dir": str(layout.run_dir)},
        {
            "contract": {
                "path": "contract/run_contract.json",
                "judgment_tradeoffs": [],
                "execution_strategy": [],
                "local_governance": [],
                "success_surface": [],
                "fake_done_states": [],
                "evidence_preferences": [],
                "residual_risk": "",
            }
        },
    )

    assert contract["judgment_tradeoffs"] == ["Evidence beats fast closure."]
    assert contract["execution_strategy"] == ["Prove inherited governance before polishing."]
    assert contract["local_governance"] == ["GateKeeper treats skipped AGENTS.md checks as Blocking."]
    assert contract["success_surface"] == ["Admin can complete the audited action."]
    assert contract["fake_done_states"] == ["Summary-only evidence is fake done."]
    assert contract["evidence_preferences"] == ["Require command output and audit artifacts."]
    assert contract["residual_risk"] == "No unmanaged residual risk is acceptable."

def test_agent_loop_revalidates_ready_bundle_file_before_start(
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
            message="Ship a ready bundle, but fail closed if the artifact changes after validation.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    ready_path = Path(generated["session"]["bundle_path"])
    ready_bundle = yaml.safe_load(ready_path.read_text(encoding="utf-8"))
    ready_bundle["spec"]["markdown"] = ready_bundle["spec"]["markdown"].replace(
        "Accept minor polish gaps only when they are explicitly named and tracked as an owned follow-up; fail closed on unproven primary-flow behavior or weak verification evidence.",
        "Some risk is fine.",
    )
    assert "Some risk is fine." in ready_bundle["spec"]["markdown"]
    ready_path.write_text(yaml.safe_dump(ready_bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")

    with pytest.raises(LooporaError, match="Residual Risk guidance"):
        service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    session = service.get_alignment_session(generated["session"]["id"])
    assert session["status"] == "ready"
    assert session["validation"]["ok"] is False
    assert any(
        event["event_type"] == "alignment_import_failed"
        and "Residual Risk guidance" in event["payload"].get("error", "")
        for event in service.list_alignment_events(session["id"])
    )

def test_agent_loop_refreshes_ready_hash_after_valid_bundle_file_change(
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
            message="Ship the focused starter experience.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    original_ready_sha = generated["binding"]["ready_candidate_sha256"]
    ready_path = Path(generated["session"]["bundle_path"])
    ready_bundle = yaml.safe_load(ready_path.read_text(encoding="utf-8"))
    ready_bundle["metadata"]["description"] = "Run from a valid canonical edit made after the first preview."
    ready_path.write_text(yaml.safe_dump(ready_bundle, sort_keys=False, allow_unicode=True), encoding="utf-8")
    expected_ready_sha, expected_ready_bytes = _ready_candidate_digest(ready_path.read_text(encoding="utf-8"))
    assert expected_ready_sha != original_ready_sha

    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)

    assert started["binding"]["ready_candidate_sha256"] == expected_ready_sha
    assert started["binding"]["ready_candidate_bytes"] == expected_ready_bytes
    assert started["session"]["validation"]["bundle_sha256"] == expected_ready_sha
    assert started["session"]["validation"]["bundle_bytes"] == expected_ready_bytes

def test_agent_native_claim_rejects_corrupted_active_capsule(
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
            message="Do not turn corrupted active capsules into partial execution contracts.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    started = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    state_path = RunArtifactLayout(Path(started["run"]["runs_dir"])).run_dir / "agent_native" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["active_step"]["capsule"] = "not-a-capsule-object"
    state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(LooporaError, match="active step capsule is invalid"):
        service.claim_agent_native_step(
            AgentNativeStepClaimRequest(adapter="codex", workdir=sample_workdir, run_id=started["run"]["id"])
        )

def test_agent_native_parallel_group_peer_context_uses_group_start_snapshot(
    service_factory,
    tmp_path: Path,
    sample_workdir: Path,
) -> None:
    service = service_factory(scenario="success")
    bundle_file = tmp_path / "bundle.yml"
    bundle_file.write_text(_alignment_bundle_yaml_with_peer_visible_parallel_review_inputs(sample_workdir), encoding="utf-8")
    service.create_agent_bundle_candidate(
        AgentBundleCandidateRequest(
            adapter="codex",
            workdir=sample_workdir,
            message="Keep agent-native parallel reviewers isolated from peer outputs.",
            bundle_file=bundle_file,
            entry_source="codex_project_skill",
        )
    )
    result = service.start_agent_loop("codex", workdir=sample_workdir, entry_source="codex_project_skill", execute_async=False)
    builder_step = result["next_step"]
    assert builder_step["action_policy"] == {
        "workspace": "workspace_write",
        "can_block": False,
        "can_finish_run": False,
    }
    assert builder_step["role"]["prompt_ref"].endswith("builder.md")
    assert "Keep implementation narrow" in builder_step["role"]["posture_notes"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(builder_step["run_id"]),
            step_id=str(builder_step["step_id"]),
            output=_agent_native_step_output(builder_step),
            host_dispatch=_agent_native_host_dispatch("codex", builder_step),
            entry_source="codex_project_skill",
        )
    )

    first_peer_step = result["next_step"]
    assert first_peer_step["step_id"] == "contract_inspection_step"
    assert first_peer_step["action_policy"] == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": False,
    }
    assert first_peer_step["role"]["prompt_ref"].endswith("inspector.md")
    assert "contract-level proof" in first_peer_step["role"]["posture_notes"]
    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(first_peer_step["run_id"]),
            step_id=str(first_peer_step["step_id"]),
            output=_agent_native_step_output(first_peer_step),
            host_dispatch=_agent_native_host_dispatch("codex", first_peer_step),
            entry_source="codex_project_skill",
        )
    )

    second_peer_step = result["next_step"]
    assert second_peer_step["step_id"] == "evidence_inspection_step"
    second_peer_context = json.loads(Path(second_peer_step["context_absolute_path"]).read_text(encoding="utf-8"))
    second_peer_handoff_steps = [item["source"]["step_id"] for item in second_peer_context["upstream"]["completed_steps_this_iteration"]]

    assert second_peer_handoff_steps == ["builder_step"]
    assert second_peer_context["evidence"]["known_ids"] == ["ev_000_00_builder_step"]
    assert second_peer_step["inputs"]["evidence_query"] == {"archetypes": ["builder", "inspector"], "limit": 12}
    assert second_peer_step["parallel_group"] == "inspection_pack"
    assert second_peer_step["known_evidence_ids"] == ["ev_000_00_builder_step"]

    result = service.submit_agent_native_step(
        AgentNativeStepSubmitRequest(
            adapter="codex",
            workdir=sample_workdir,
            run_id=str(second_peer_step["run_id"]),
            step_id=str(second_peer_step["step_id"]),
            output=_agent_native_step_output(second_peer_step),
            host_dispatch=_agent_native_host_dispatch("codex", second_peer_step),
            entry_source="codex_project_skill",
        )
    )

    gatekeeper_step = result["next_step"]
    assert gatekeeper_step["step_id"] == "gatekeeper_step"
    assert gatekeeper_step["action_policy"] == {
        "workspace": "read_only",
        "can_block": True,
        "can_finish_run": True,
    }
    assert gatekeeper_step["role"]["prompt_ref"].endswith("gatekeeper.md")
    assert "Close only when" in gatekeeper_step["role"]["posture_notes"]
    gatekeeper_context = json.loads(Path(gatekeeper_step["context_absolute_path"]).read_text(encoding="utf-8"))
    gatekeeper_handoff_steps = [item["source"]["step_id"] for item in gatekeeper_context["upstream"]["completed_steps_this_iteration"]]

    assert gatekeeper_handoff_steps == ["contract_inspection_step", "evidence_inspection_step"]
    assert {
        "ev_000_01_contract_inspection_step",
        "ev_000_02_evidence_inspection_step",
    }.issubset(set(gatekeeper_context["evidence"]["known_ids"]))
    events = service.stream_events(str(gatekeeper_step["run_id"]), limit=200)
    assert any(
        event["event_type"] == "parallel_group_started"
        and event["payload"]["parallel_group"] == "inspection_pack"
        and event["payload"]["step_ids"] == ["contract_inspection_step", "evidence_inspection_step"]
        for event in events
    )
    assert any(
        event["event_type"] == "parallel_group_finished"
        and event["payload"]["parallel_group"] == "inspection_pack"
        and event["payload"]["step_ids"] == ["contract_inspection_step", "evidence_inspection_step"]
        for event in events
    )
