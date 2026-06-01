from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    CliRunner,
    LooporaConflictError,
    LooporaError,
    Path,
    _assert_agent_run_summary_for_started_run,
    _assert_codex_native_surface_summary,
    _candidate_digest,
    _drive_agent_native_run_to_success,
    _ready_candidate_digest,
    alignment_bundle_yaml,
    cli,
    cli_agent_adapter_commands,
    hashlib,
    json,
    pytest,
    yaml,
)


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
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready")
    assert summary["ready"] is True
    assert summary["status"] == "ready"
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert "run" not in summary


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
        raise AssertionError(f"Agent-first imported sessions must not start an automation runner for {run_id}")

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
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready")
    assert summary["ready"] is True


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
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_plan", summary_key="agent_plan_summary", status="ready")
    assert summary["ready"] is True
    assert summary["status"] == "ready"
    assert summary["preview_url"].startswith("/loops/new/bundle?alignment_session_id=")
    assert "run" not in summary


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

    cli_agent_adapter_commands._attach_agent_run_summary(result)

    summary = result["agent_run_summary"]
    assert summary["dispatch_next"] == (
        "invoke loopora-builder with the next context and step contract paths below; do not perform this role inline"
    )
    assert summary["next_step"]["dispatch_next"] == summary["dispatch_next"]
    _assert_codex_native_surface_summary(summary)


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
