from __future__ import annotations

import errno

from agent_adapter_source_checkout_help_cases import (
    assert_cli_adapter_install_managed_entries_preserve_current_cli_entry,
    assert_project_file_cli_entry_anchors_source_checkout_uv_commands,
    assert_source_checkout_help_command_rewrite_is_idempotent,
    assert_source_checkout_help_epilogs_preserve_project_file_cli_entry,
    monkeypatch_source_checkout_cli_entry,
)
from compacted_agent_native_support import adapter_entry_paths_text, assert_first_task_message_example, assert_native_surface_payload
from agent_adapter_test_support import CliRunner, Path, _assert_loopora_cli_command, assert_adapter_group_previews_keep_peer_adapter_choices, assert_init_group_workdir_preview, cli, json, pytest, shlex
from cli_first_use_docs_test_support import complete_fit_review_cli_args
from loopora.branding import APP_HOME_ENV
from loopora.agent_adapter_current_host import current_agent_host_detection
from loopora.settings import load_recent_workdirs

CURRENT_HOST_ENV = {
    "CODEX_SESSION_ID": "",
    "CODEX_THREAD_ID": "",
    "CLAUDE_SESSION_ID": "",
    "OPENCODE_SESSION_ID": "",
}


@pytest.mark.parametrize(
    ("environ", "state", "adapter", "detected"),
    [
        ({}, "unavailable", "", []),
        ({"CODEX_THREAD_ID": "private-codex-id"}, "detected", "codex", ["codex"]),
        ({"CLAUDE_SESSION_ID": "private-claude-id"}, "detected", "claude", ["claude"]),
        ({"OPENCODE_SESSION_ID": "private-opencode-id"}, "detected", "opencode", ["opencode"]),
        ({"CODEX_THREAD_ID": "private-codex-id", "CLAUDE_SESSION_ID": "private-claude-id"}, "ambiguous", "", ["codex", "claude"]),
    ],
)
def test_current_agent_host_detection_is_unique_and_redacted(environ, state: str, adapter: str, detected: list[str]) -> None:
    payload = current_agent_host_detection(environ)

    assert payload["state"] == state
    assert payload["adapter"] == adapter
    assert payload["detected_adapters"] == detected
    assert "private-" not in json.dumps(payload)


@pytest.mark.parametrize(
    ("signals", "state", "adapter", "selection_required"),
    [
        ({}, "unavailable", "", True),
        ({"CODEX_THREAD_ID": "private-codex-id"}, "detected", "codex", False),
        ({"CODEX_THREAD_ID": "private-codex-id", "CLAUDE_SESSION_ID": "private-claude-id"}, "ambiguous", "", True),
    ],
)
def test_start_fit_same_agent_route_follows_current_host_detection(tmp_path: Path, signals, state: str, adapter: str, selection_required) -> None:
    workdir = tmp_path / "route-project"
    workdir.mkdir()
    env = {**CURRENT_HOST_ENV, **signals}
    args = ["--workdir", str(workdir), *complete_fit_review_cli_args()]
    payloads = []
    for surface in ("start", "fit"):
        result = CliRunner().invoke(cli.app, [surface, *args, "--json"], env=env)
        assert result.exit_code == 0, result.stdout
        assert "private-" not in result.stdout
        payloads.append(json.loads(result.stdout))
    for payload in payloads:
        setup = next(action for action in payload["route_actions_after_strong_fit"] if action["kind"] == "install_agent_entry")
        assert (payload["current_agent_host"]["state"], payload["current_agent_host"]["adapter"]) == (state, adapter)
        assert (setup["selection_required"], setup["adapter_fallback_available"], "command" in setup) == (selection_required, selection_required, not selection_required)
        assert (setup["action_ready"], setup["command_ready"], setup["ready_adapter_choice_count"]) == (True, not selection_required, 3 if selection_required else 0)
        assert all(choice["fallback_applicable"] is selection_required for choice in setup["adapter_choices"])
    details = CliRunner().invoke(cli.app, ["start", *args, "--details"], env=env)
    assert details.exit_code == 0, details.stdout
    assert ("init current" in details.stdout, "init codex" in details.stdout) == (not selection_required, selection_required)


@pytest.mark.parametrize(
    ("adapter", "signal", "entry_path"),
    [
        ("codex", "CODEX_THREAD_ID", ".agents/skills/loopora-plan/SKILL.md"),
        ("claude", "CLAUDE_SESSION_ID", ".claude/skills/loopora-plan/SKILL.md"),
        ("opencode", "OPENCODE_SESSION_ID", ".opencode/commands/loopora-plan.md"),
    ],
)
def test_cli_init_current_installs_only_the_uniquely_detected_host(tmp_path: Path, adapter: str, signal: str, entry_path: str) -> None:
    workdir = tmp_path / adapter
    app_home = tmp_path / f"home-{adapter}"
    workdir.mkdir()
    app_home.mkdir()
    env = {**CURRENT_HOST_ENV, signal: "private-session-id", APP_HOME_ENV: str(app_home)}

    result = CliRunner().invoke(cli.app, ["init", "current", "--workdir", str(workdir), "--json"], env=env)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["adapter"] == adapter
    assert payload["kind"] == "same_agent_setup"
    assert payload["setup_status"] == "ready"
    assert payload["setup_ready"] is True
    assert payload["readiness"]["first_task_handoff_executable"] is True
    assert "private-session-id" not in result.stdout
    assert (workdir / entry_path).is_file()


def test_cli_init_current_fails_closed_when_host_is_missing_or_ambiguous(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "project"
    workdir.mkdir()

    missing = runner.invoke(cli.app, ["init", "current", "--workdir", str(workdir), "--json"], env=CURRENT_HOST_ENV)
    ambiguous = runner.invoke(
        cli.app,
        ["init", "current", "--workdir", str(workdir), "--json"],
        env={**CURRENT_HOST_ENV, "CODEX_THREAD_ID": "codex-secret", "CLAUDE_SESSION_ID": "claude-secret"},
    )

    assert missing.exit_code == ambiguous.exit_code == 1
    assert json.loads(missing.stdout)["current_agent_host"]["state"] == "unavailable"
    ambiguous_payload = json.loads(ambiguous.stdout)
    assert ambiguous_payload["current_agent_host"]["state"] == "ambiguous"
    assert [item["adapter"] for item in ambiguous_payload["adapter_choices"]] == ["codex", "claude", "opencode"]
    assert not any((workdir / root).exists() for root in (".agents", ".claude", ".opencode"))
    assert "codex-secret" not in ambiguous.stdout
    assert "claude-secret" not in ambiguous.stdout

def expected_first_task_handoff_policy(workdir: Path) -> dict[str, str]:
    fit_command = f"loopora fit --workdir {shlex.quote(str(workdir.resolve()))}"
    return {
        "preferred_source": "completed_fit_review",
        "fallback_source": "generic_example",
        "fit_command": fit_command,
        "plan_command": "/loopora-plan",
        "copy_rule": (
            f"If you completed {fit_command} with task review, paste its copyable /loopora-plan handoff as one Agent message; "
            "otherwise use the generic orientation example only as a review starting point."
        ),
    }

def test_cli_init_group_accepts_workdir_preview_without_choosing_adapter(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "target project"
    app_home = tmp_path / "loopora-home"
    workdir.mkdir()
    app_home.mkdir()
    normalized_workdir = shlex.quote(str(workdir.resolve()))
    monkeypatch.setattr("loopora.cli_agent_group_previews.web_bind_preflight.probe_web_bind", lambda *_args: None)

    result = runner.invoke(cli.app, ["init", "--workdir", str(workdir)], env={APP_HOME_ENV: str(app_home)})

    assert_init_group_workdir_preview(result, normalized_workdir=normalized_workdir)


def test_cli_init_group_workdir_preview_uses_available_web_port(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "target project"
    app_home = tmp_path / "loopora-home"
    workdir.mkdir()
    app_home.mkdir()
    normalized_workdir = shlex.quote(str(workdir.resolve()))

    def fail_default_port(_host: str, port: int) -> None:
        if port == 8742:
            raise OSError(errno.EADDRINUSE, "busy")

    monkeypatch.setattr("loopora.cli_agent_group_previews.web_bind_preflight.probe_web_bind", fail_default_port)
    monkeypatch.setattr("loopora.cli_agent_group_previews.web_bind_preflight.next_available_web_port", lambda **_kwargs: 9876)

    result = runner.invoke(cli.app, ["init", "--workdir", str(workdir)], env={APP_HOME_ENV: str(app_home)})

    assert result.exit_code == 0, result.stdout
    assert "Default Web port 8742 is already in use; this preview uses available port 9876." in result.stdout
    assert f"loopora serve --open --workdir {normalized_workdir} --host 127.0.0.1 --port 9876" in result.stdout


def test_cli_init_group_workdir_preview_marks_app_web_readiness_blockers(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "target project"
    workdir.mkdir()
    normalized_workdir = shlex.quote(str(workdir.resolve()))
    monkeypatch.setattr("loopora.cli_agent_group_previews.web_bind_preflight.probe_web_bind", lambda *_args: None)
    monkeypatch.setattr(
        "loopora.cli_agent_group_previews.first_use_web_readiness_blockers",
        lambda _state: [
            {
                "kind": "app_state_not_ready",
                "status": "development_reset_required",
                "recovery_action": "preview_app_database_reset",
            }
        ],
    )

    result = runner.invoke(cli.app, ["init", "--workdir", str(workdir)])

    assert result.exit_code == 0, result.stdout
    assert "App/Web readiness needs attention; run doctor before starting Web." in result.stdout
    assert "Fit Guide/Web choices after App/Web readiness:" in result.stdout
    assert f"loopora serve --open --workdir {normalized_workdir} --host 127.0.0.1 --port 8742" in result.stdout


def test_cli_init_group_workdir_before_adapter_is_not_dropped(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "chosen-project"
    workdir.mkdir()

    result = runner.invoke(cli.app, ["init", "--workdir", str(workdir), "codex", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["workdir"] == str(workdir.resolve())
    assert f"loopora doctor --workdir {workdir.resolve()}" in payload["next_commands"]["doctor"]
    assert f"loopora serve --open --workdir {workdir.resolve()}" in payload["next_commands"]["web_start"]
    assert f"loopora support --workdir {workdir.resolve()}" in payload["next_commands"]["support"]


def test_cli_adapter_group_workdirs_preview_and_flow_into_subcommands(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir = tmp_path / "target project"
    app_home = tmp_path / "loopora home"
    workdir.mkdir()
    app_home.mkdir()
    env = {APP_HOME_ENV: str(app_home)}
    workdir_arg = shlex.quote(str(workdir.resolve()))

    uninstall_preview = runner.invoke(cli.app, ["uninstall", "--workdir", str(workdir)], env=env)
    agent_preview = runner.invoke(cli.app, ["agent", "--workdir", str(workdir)], env=env)
    agent_codex_preview = runner.invoke(cli.app, ["agent", "codex", "--workdir", str(workdir)], env=env)

    assert uninstall_preview.exit_code == 0, uninstall_preview.output
    assert agent_preview.exit_code == 0, agent_preview.output
    assert agent_codex_preview.exit_code == 0, agent_codex_preview.output
    for result in (uninstall_preview, agent_preview, agent_codex_preview):
        assert result.stdout.startswith("Target project preview:")
        assert "Usage:" not in result.stdout
    assert "preview state: ready for adapter choice" in uninstall_preview.stdout
    assert "project directory state: ready" in uninstall_preview.stdout
    assert f"loopora uninstall codex --workdir {workdir_arg}" in uninstall_preview.stdout
    assert f"loopora doctor --workdir {workdir_arg}" in uninstall_preview.stdout
    assert f"loopora support --workdir {workdir_arg}" in uninstall_preview.stdout
    assert "preview state: ready for adapter choice" in agent_preview.stdout
    assert "project directory state: ready" in agent_preview.stdout
    assert f"loopora agent codex check --workdir {workdir_arg}" in agent_preview.stdout
    assert f"loopora support --workdir {workdir_arg}" in agent_preview.stdout
    assert "preview state: ready for adapter choice" in agent_codex_preview.stdout
    assert "project directory state: ready" in agent_codex_preview.stdout
    assert f"loopora agent codex check --workdir {workdir_arg}" in agent_codex_preview.stdout
    assert f"loopora support --workdir {workdir_arg}" in agent_codex_preview.stdout
    assert "No such option: --workdir" not in uninstall_preview.output + agent_preview.output + agent_codex_preview.output
    assert "Installing" not in uninstall_preview.stdout + agent_preview.stdout + agent_codex_preview.stdout
    assert_adapter_group_previews_keep_peer_adapter_choices(
        uninstall_stdout=uninstall_preview.stdout,
        agent_stdout=agent_preview.stdout,
    )

    uninstall = runner.invoke(cli.app, ["uninstall", "--workdir", str(workdir), "codex", "--json"], env=env)
    check_from_agent_group = runner.invoke(cli.app, ["agent", "--workdir", str(workdir), "codex", "check", "--json"], env=env)
    check_from_adapter_group = runner.invoke(cli.app, ["agent", "codex", "--workdir", str(workdir), "check", "--json"], env=env)
    plan_from_agent_group = runner.invoke(
        cli.app,
        [
            "agent",
            "--workdir",
            str(workdir),
            "codex",
            "plan",
            "--message",
            "Goal: check target propagation; Fake-done risks: none; Required evidence: smoke; Judgment tradeoffs: narrow",
            "--compact-json",
            "--no-web",
        ],
        env=env,
    )

    assert uninstall.exit_code == 0, uninstall.stdout
    assert json.loads(uninstall.stdout)["workdir"] == str(workdir.resolve())
    for result in (check_from_agent_group, check_from_adapter_group):
        assert result.exit_code == 1, result.stdout
        payload = json.loads(result.stdout)
        assert payload["summary"]["workdir"] == str(workdir.resolve())
        assert f"loopora init codex --workdir {workdir_arg}" in payload["summary"]["check_recovery"]["install_command"]
    assert plan_from_agent_group.exit_code == 0, plan_from_agent_group.stdout
    assert json.loads(plan_from_agent_group.stdout)["summary"]["workdir"] == str(workdir.resolve())


def test_cli_adapter_group_workdir_previews_gate_unusable_targets(tmp_path: Path) -> None:
    runner = CliRunner()
    missing_workdir = tmp_path / "missing project"
    workdir_file = tmp_path / "not-a-project"
    workdir_file.write_text("not a directory\n", encoding="utf-8")
    missing_arg = shlex.quote(str(missing_workdir.resolve()))
    file_arg = shlex.quote(str(workdir_file.resolve()))

    missing_previews = [
        runner.invoke(cli.app, ["init", "--workdir", str(missing_workdir)]),
        runner.invoke(cli.app, ["uninstall", "--workdir", str(missing_workdir)]),
        runner.invoke(cli.app, ["agent", "--workdir", str(missing_workdir)]),
        runner.invoke(cli.app, ["agent", "codex", "--workdir", str(missing_workdir)]),
    ]

    for result in missing_previews:
        assert result.exit_code == 0, result.output
        assert result.stdout.startswith("Target project preview:")
        assert "Usage:" not in result.stdout
        preview = result.stdout.split("Target project preview:", 1)[1]
        assert "preview state: blocked by project directory" in preview
        assert "project directory state: missing" in preview
        assert "Target project directory does not exist yet" in preview
        assert f"mkdir -p {missing_arg}" in preview
        assert preview.index("Create target project directory") < preview.index("loopora doctor --workdir")
        assert not missing_workdir.exists()

    file_previews = [
        runner.invoke(cli.app, ["init", "--workdir", str(workdir_file)]),
        runner.invoke(cli.app, ["uninstall", "--workdir", str(workdir_file)]),
        runner.invoke(cli.app, ["agent", "--workdir", str(workdir_file)]),
        runner.invoke(cli.app, ["agent", "codex", "--workdir", str(workdir_file)]),
    ]

    for result in file_previews:
        assert result.exit_code == 0, result.output
        assert result.stdout.startswith("Target project preview:")
        assert "Usage:" not in result.stdout
        preview = result.stdout.split("Target project preview:", 1)[1]
        assert "preview state: blocked by project directory" in preview
        assert "project directory state: not_directory" in preview
        assert "Target project path exists but is not a directory" in preview
        assert "Choose project directory" in preview
        assert "mkdir -p" not in preview
        assert f"--workdir {file_arg}" not in preview
        assert "loopora doctor --workdir" not in preview


def test_cli_agent_adapter_groups_recover_unsupported_adapter_and_accept_aliases() -> None:
    runner = CliRunner()

    for args in (["init", "cursor"], ["uninstall", "cursor"], ["agent", "cursor", "check"]):
        result = runner.invoke(cli.app, args)
        assert result.exit_code == 2, result.output
        assert "No such command" not in result.output
        assert "unsupported Agent adapter" in result.stdout
        assert "supported Agent adapters: codex, claude, opencode" in result.stdout
        assert "supported aliases:" in result.stdout
        assert 'loopora doctor --workdir "$PWD"' in result.stdout
        assert 'loopora support --workdir "$PWD"' in result.stdout
        expected_labels = {
            "init": (
                "Check fit first",
                "Install supported same-Agent project entry",
                "Confirm readiness",
                "Usage/setup help",
            ),
            "uninstall": (
                "Choose supported same-Agent project entry",
                "Review installed entries",
                "Usage/setup help",
            ),
            "agent": (
                "Check supported same-Agent project entry",
                "Install supported same-Agent project entry",
                "Confirm readiness",
                "Usage/setup help",
            ),
        }[args[0]]
        assert all(label in result.stdout for label in expected_labels)
        expected = "loopora agent {adapter} check --workdir" if args[0] == "agent" else f"loopora {args[0]} {{adapter}} --workdir"
        assert all(expected.format(adapter=adapter) in result.stdout for adapter in ("codex", "claude", "opencode"))
        assert all(fragment not in result.stdout for fragment in ("loopora init --workdir", "loopora agent --workdir", "loopora uninstall --workdir"))
        assert "match your current Agent host" in result.stdout

    json_result = runner.invoke(cli.app, ["init", "cursor", "--json"])
    assert json_result.exit_code == 2, json_result.output
    payload = json.loads(json_result.stdout)
    summary = payload["unsupported_agent_adapter_summary"]
    assert (summary["ready"], summary["status"], summary["adapter"]) == (False, "unsupported_agent_adapter", "cursor")
    assert (summary["command_group"], summary["supported_adapters"]) == ("init", ["codex", "claude", "opencode"])
    assert summary["next_action_kinds"] == ["check_fit_first", "install_supported_agent_entry", "confirm_readiness", "support"]
    assert summary["next_action_ready_now_kinds"] == summary["next_action_kinds"]
    assert summary["next_action_ready_after_actions"] == {}
    assert [action["kind"] for action in payload["next_actions"]] == [
        "check_fit_first",
        "install_supported_agent_entry",
        "confirm_readiness",
        "support",
    ]
    install_action = payload["next_actions"][1]
    assert install_action["selection_required"] is True
    assert [choice["adapter"] for choice in install_action["adapter_choices"]] == ["codex", "claude", "opencode"]
    assert all(f"loopora init {choice['adapter']} --workdir" in choice["command"] for choice in install_action["adapter_choices"])
    assert payload["next_actions"][1]["note"] == "Choose codex, claude, or opencode to match your current Agent host."

    claude_alias_help = runner.invoke(cli.app, ["init", "claude-code", "--help"])
    opencode_alias_help = runner.invoke(cli.app, ["agent", "open-code", "check", "--help"])
    assert claude_alias_help.exit_code == 0, claude_alias_help.output
    assert "Claude Code project entry" in claude_alias_help.stdout
    assert opencode_alias_help.exit_code == 0, opencode_alias_help.output
    assert "Check the Loopora-managed project entry" in opencode_alias_help.stdout


def test_cli_unsupported_agent_adapter_recovery_preserves_explicit_workdir(tmp_path: Path) -> None:
    runner = CliRunner()
    ready_workdir = tmp_path / "ready project"
    missing_workdir = tmp_path / "missing project"
    ready_workdir.mkdir()
    ready_arg = shlex.quote(str(ready_workdir.resolve()))
    missing_arg = shlex.quote(str(missing_workdir.resolve()))

    ready_result = runner.invoke(cli.app, ["init", "--workdir", str(ready_workdir), "cursor", "--json"])
    missing_result = runner.invoke(cli.app, ["agent", "cursor", "check", "--workdir", str(missing_workdir), "--json"])

    assert ready_result.exit_code == 2, ready_result.output
    ready_payload = json.loads(ready_result.stdout)
    assert ready_payload["unsupported_agent_adapter_summary"]["workdir"] == str(ready_workdir.resolve())
    assert ready_payload["workdir_state"]["status"] == "ready"
    ready_choices = ready_payload["next_actions"][1]["adapter_choices"]
    assert all(f"loopora init {choice['adapter']} --workdir {ready_arg}" in choice["command"] for choice in ready_choices)
    assert f"loopora doctor --workdir {ready_arg}" in ready_payload["next_actions"][2]["command"]
    assert f"loopora support --workdir {ready_arg}" in ready_payload["next_actions"][3]["command"]
    assert f"loopora init --workdir {ready_arg}" not in ready_result.stdout

    assert missing_result.exit_code == 2, missing_result.output
    assert not missing_workdir.exists()
    missing_payload = json.loads(missing_result.stdout)
    assert missing_payload["unsupported_agent_adapter_summary"]["workdir"] == str(missing_workdir.resolve())
    assert missing_payload["workdir_state"]["status"] == "missing"
    assert missing_payload["next_actions"][0] == {"kind": "create_workdir", "command": f"mkdir -p {missing_arg}"}
    assert missing_payload["next_action_ready_now_kinds"] == ["create_workdir", "support"]
    assert missing_payload["unsupported_agent_adapter_summary"]["next_action_ready_after_actions"] == {
        "check_supported_agent_entry": "create_workdir",
        "install_supported_agent_entry": "create_workdir",
        "confirm_readiness": "create_workdir",
    }
    missing_choices = missing_payload["next_actions"][1]["adapter_choices"]
    assert all(f"loopora agent {choice['adapter']} check --workdir {missing_arg}" in choice["command"] for choice in missing_choices)
    assert f"loopora doctor --workdir {missing_arg}" in missing_payload["next_actions"][3]["command"]
    assert f"loopora support --workdir {missing_arg}" in missing_payload["next_actions"][4]["command"]
    assert f"loopora agent --workdir {missing_arg}" not in missing_result.stdout


def test_cli_unsupported_agent_adapter_recovery_gates_unusable_workdir(tmp_path: Path) -> None:
    runner = CliRunner()
    workdir_file = tmp_path / "not-a-project"
    workdir_file.write_text("not a directory\n", encoding="utf-8")
    bad_arg = shlex.quote(str(workdir_file.resolve()))

    plain = runner.invoke(cli.app, ["uninstall", "cursor", "--workdir", str(workdir_file)])
    structured = runner.invoke(cli.app, ["uninstall", "cursor", "--workdir", str(workdir_file), "--json"])

    assert plain.exit_code == 2, plain.output
    assert "unsupported Agent adapter" in plain.stdout
    assert "project directory state: not_directory" in plain.stdout
    assert "Choose an existing project directory" in plain.stdout
    assert "Usage/setup help" in plain.stdout
    assert f"loopora support --workdir {bad_arg}" in plain.stdout
    assert f"loopora uninstall codex --workdir {bad_arg}" not in plain.stdout
    assert "loopora doctor --workdir" not in plain.stdout

    assert structured.exit_code == 2, structured.output
    payload = json.loads(structured.stdout)
    assert payload["workdir"] == str(workdir_file.resolve())
    assert payload["workdir_state"]["status"] == "not_directory"
    next_kinds = [item["kind"] for item in payload["next_actions"]]
    assert payload["unsupported_agent_adapter_summary"]["next_action_kinds"] == next_kinds == ["choose_workdir", "choose_supported_agent_entry", "support"]
    assert payload["next_action_ready_now_kinds"] == ["choose_workdir", "support"]
    assert payload["unsupported_agent_adapter_summary"]["next_action_ready_after_actions"] == {
        "choose_supported_agent_entry": "choose_workdir",
    }
    assert all("command" not in item for item in payload["next_actions"][:2])
    assert f"loopora support --workdir {bad_arg}" in structured.stdout
    assert f"loopora uninstall codex --workdir {bad_arg}" not in structured.stdout

@pytest.mark.parametrize(
    ("adapter", "label"),
    [
        ("codex", "Codex"),
        ("claude", "Claude Code"),
        ("opencode", "OpenCode"),
    ],
)
def test_cli_adapter_install_human_output_points_to_agent_next_steps(
    monkeypatch,
    tmp_path: Path,
    adapter: str,
    label: str,
) -> None:
    workdir = tmp_path / adapter
    workdir.mkdir()
    runner = CliRunner()
    entry_paths = adapter_entry_paths_text(adapter)
    source_entry = monkeypatch_source_checkout_cli_entry(monkeypatch)

    result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir)])

    assert result.exit_code == 0, result.stdout
    output = result.stdout
    expected_snippets = (
        f"{label} Loopora entry is installed",
        f"target project: {workdir.resolve()}",
        "next:",
        f"Confirm local readiness before returning to {label}:",
        f"loopora doctor --workdir {workdir.resolve()}",
        f"Return to {label} in this project",
        "Loopora fit reason, task goal, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context",
        "/loopora-plan",
        "READY Loop preview",
        "/loopora-run",
        "same Agent session",
        "If /loopora-plan or /loopora-run is not visible",
        entry_paths,
        f"refresh or restart {label}",
        "Fit Guide first, then creation choices: Web conversation outside an Agent session",
        "Plan File import",
        "manual expert paths",
        "review evidence, gaps, and verdicts",
        "first task message handoff:",
        "completed fit review:",
        f"{source_entry} fit",
        "paste its copyable /loopora-plan handoff as one Agent message",
        "generic orientation example (not a completed review):",
        "diagnostics:",
        "- readiness report:",
        f"loopora doctor --workdir {workdir.resolve()}",
        "- verify install:",
        f"loopora init {adapter} --workdir {workdir.resolve()} --check",
        "- agent-runtime check:",
        f"loopora agent {adapter} check --workdir {workdir.resolve()}",
        "- usage/setup help:",
        f"loopora support --workdir {workdir.resolve()}",
        "web:",
        "- after readiness passes, open Fit Guide/Web choices in Web:",
        f"loopora serve --open --workdir {workdir.resolve()} --host 127.0.0.1 --port 8742",
        "installed files:",
        "managed files current",
        "manifest:",
        "details: rerun with --json for managed file hashes and the Agent surface contract.",
    )
    forbidden_snippets = ("agent surface:", "managed files:", "adapter installed", "YAML bundle")
    assert not [snippet for snippet in expected_snippets if snippet not in output]
    assert output.index(f"Confirm local readiness before returning to {label}:") < output.index(
        f"Return to {label} in this project"
    )
    assert output.index(f"Confirm local readiness before returning to {label}:") < output.index(
        "Run /loopora-plan to prepare the Loop preview before starting work."
    )
    assert output.index("If /loopora-plan or /loopora-run is not visible") < output.index(
        "Run /loopora-plan to prepare the Loop preview before starting work."
    )
    assert output.index("diagnostics:") < output.index("web:")
    assert output.index("- readiness report:") < output.index("- after readiness passes, open Fit Guide/Web choices in Web:")
    assert output.index("completed fit review:") < output.index("generic orientation example")
    assert output.index("generic orientation example") < output.index("/loopora-plan\n\nLoopora fit:")
    assert not any(snippet in output for snippet in forbidden_snippets)
    assert_first_task_message_example(output)

    json_result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert any("Confirm local readiness before returning" in item for item in payload["next_steps"])
    assert any(f"Return to {label}" in item for item in payload["next_steps"])
    assert any("/loopora-plan" in item for item in payload["next_steps"])
    assert any("/loopora-run" in item for item in payload["next_steps"])
    encoded_next_steps = json.dumps(payload["next_steps"], ensure_ascii=False)
    assert "Fit Guide first, then creation choices: Web conversation outside an Agent session" in encoded_next_steps
    assert "Plan File import" in encoded_next_steps
    assert "manual expert paths" in encoded_next_steps
    assert any(entry_paths in item for item in payload["next_steps"])
    assert any(f"refresh or restart {label}" in item for item in payload["next_steps"])
    visibility_step = next(item for item in payload["next_steps"] if entry_paths in item)
    plan_step = next(item for item in payload["next_steps"] if "Run /loopora-plan" in item)
    assert payload["next_steps"].index(visibility_step) < payload["next_steps"].index(plan_step)
    assert_first_task_message_example(payload["first_task_message_example"])
    assert payload["first_task_handoff_policy"] == expected_first_task_handoff_policy(workdir)
    assert payload["next_commands"]["plan"] == "/loopora-plan"
    assert payload["next_commands"]["run"] == "/loopora-run"
    _assert_loopora_cli_command(
        payload["next_commands"]["web_start"],
        f"loopora serve --open --workdir {workdir.resolve()} --host 127.0.0.1 --port 8742",
    )
    assert_native_surface_payload(payload, adapter=adapter, entry_paths=entry_paths)
    _assert_loopora_cli_command(
        payload["next_commands"]["doctor"],
        f"loopora doctor --workdir {workdir.resolve()}",
    )
    _assert_loopora_cli_command(
        payload["next_commands"]["check"],
        f"loopora init {adapter} --workdir {workdir.resolve()} --check",
    )
    _assert_loopora_cli_command(
        payload["next_commands"]["agent_check"],
        f"loopora agent {adapter} check --workdir {workdir.resolve()}",
    )
    _assert_loopora_cli_command(
        payload["next_commands"]["support"],
        f"loopora support --workdir {workdir.resolve()}",
    )


@pytest.mark.parametrize(
    ("adapter", "entry_source", "entry_root"),
    [
        ("codex", "codex_project_skill", ".agents/skills"),
        ("claude", "claude_project_skill", ".claude/skills"),
        ("opencode", "opencode_project_command", ".opencode"),
    ],
)
def test_cli_adapter_install_managed_entries_preserve_current_cli_entry(
    monkeypatch,
    tmp_path: Path,
    adapter: str,
    entry_source: str,
    entry_root: str,
) -> None:
    assert_cli_adapter_install_managed_entries_preserve_current_cli_entry(
        monkeypatch,
        tmp_path,
        adapter=adapter,
        entry_source=entry_source,
        entry_root=entry_root,
    )


def test_project_file_cli_entry_anchors_source_checkout_uv_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    assert_project_file_cli_entry_anchors_source_checkout_uv_commands(monkeypatch)


def test_source_checkout_help_command_rewrite_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    assert_source_checkout_help_command_rewrite_is_idempotent(monkeypatch)


def test_source_checkout_help_epilogs_preserve_project_file_cli_entry() -> None:
    assert_source_checkout_help_epilogs_preserve_project_file_cli_entry()


def test_cli_adapter_install_repairs_corrupt_recent_workdirs_without_terminal_warning(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_home = tmp_path / "app-home"
    workdir = tmp_path / "project"
    app_home.mkdir()
    workdir.mkdir()
    (app_home / "recent_workdirs.json").write_text("{not json}\n", encoding="utf-8")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))
    runner = CliRunner()

    result = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir)])

    assert result.exit_code == 0, result.stdout
    terminal_output = result.stdout + result.stderr
    assert "Codex Loopora entry is installed" in terminal_output
    assert "settings.recent_workdirs.read_failed" not in terminal_output
    assert "Failed to read recent workdirs" not in terminal_output
    assert load_recent_workdirs() == [str(workdir.resolve())]


@pytest.mark.parametrize(
    ("adapter", "label", "expected_removed_path"),
    [
        ("codex", "Codex", ".agents/skills/loopora-plan/SKILL.md"),
        ("claude", "Claude Code", ".claude/skills/loopora-plan/SKILL.md"),
        ("opencode", "OpenCode", ".opencode/commands/loopora-plan.md"),
    ],
)
def test_cli_adapter_uninstall_dry_run_previews_scope_without_deleting(
    monkeypatch,
    tmp_path: Path,
    adapter: str,
    label: str,
    expected_removed_path: str,
) -> None:
    workdir = tmp_path / f"{adapter} project"
    json_workdir = tmp_path / f"{adapter} json project"
    workdir.mkdir()
    json_workdir.mkdir()
    runner = CliRunner()
    monkeypatch_source_checkout_cli_entry(monkeypatch)

    install = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])
    preview = runner.invoke(cli.app, ["uninstall", adapter, "--workdir", str(workdir), "--dry-run"])
    json_install = runner.invoke(cli.app, ["init", adapter, "--workdir", str(json_workdir), "--json"])
    json_preview = runner.invoke(cli.app, ["uninstall", adapter, "--workdir", str(json_workdir), "--dry-run", "--json"])

    assert install.exit_code == 0, install.stdout
    assert preview.exit_code == 0, preview.stdout
    assert f"{label} Loopora entry uninstall dry run" in preview.stdout
    assert f"target project: {workdir.resolve()}" in preview.stdout
    assert "would remove:" in preview.stdout
    assert "After reviewing the dry-run scope:" in preview.stdout
    assert expected_removed_path not in preview.stdout
    assert (workdir / expected_removed_path).exists()
    assert json_install.exit_code == 0, json_install.stdout
    assert json_preview.exit_code == 0, json_preview.stdout
    preview_payload = json.loads(json_preview.stdout)
    assert preview_payload["status"] == "dry_run"
    assert preview_payload["dry_run"] is True
    assert expected_removed_path in preview_payload["removed_files"]
    assert (json_workdir / expected_removed_path).exists()


@pytest.mark.parametrize(
    ("adapter", "label", "expected_removed_path"),
    [
        ("codex", "Codex", ".agents/skills/loopora-plan/SKILL.md"),
        ("claude", "Claude Code", ".claude/skills/loopora-plan/SKILL.md"),
        ("opencode", "OpenCode", ".opencode/commands/loopora-plan.md"),
    ],
)
def test_cli_adapter_uninstall_human_output_summarizes_cleanup_while_json_keeps_paths(
    monkeypatch,
    tmp_path: Path,
    adapter: str,
    label: str,
    expected_removed_path: str,
) -> None:
    workdir = tmp_path / f"{adapter} project"
    workdir.mkdir()
    runner = CliRunner()
    source_entry = monkeypatch_source_checkout_cli_entry(monkeypatch)

    install = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])
    result = runner.invoke(cli.app, ["uninstall", adapter, "--workdir", str(workdir)])

    assert install.exit_code == 0, install.stdout
    assert result.exit_code == 0, result.stdout
    assert f"{label} Loopora entry is uninstalled" in result.stdout
    assert f"target project: {workdir.resolve()}" in result.stdout
    assert "removed files:" in result.stdout
    assert "Loopora-managed files" in result.stdout
    assert "kept files: none" in result.stdout
    assert "next:" in result.stdout
    assert "Reinstall later:" in result.stdout
    assert f"{source_entry} init {adapter} --workdir {shlex.quote(str(workdir.resolve()))}" in result.stdout
    assert f"loopora init {adapter} --workdir {shlex.quote(str(workdir.resolve()))}" in result.stdout
    assert f"refresh or restart {label}" in result.stdout
    assert "details: pass --json when you need exact removed and kept paths for cleanup logs." in result.stdout
    assert "uninstalled: not_installed" not in result.stdout
    assert "removed:" not in result.stdout
    assert expected_removed_path not in result.stdout

    json_workdir = tmp_path / f"{adapter} json project"
    json_workdir.mkdir()
    json_install = runner.invoke(cli.app, ["init", adapter, "--workdir", str(json_workdir), "--json"])
    json_uninstall = runner.invoke(cli.app, ["uninstall", adapter, "--workdir", str(json_workdir), "--json"])

    assert json_install.exit_code == 0, json_install.stdout
    assert json_uninstall.exit_code == 0, json_uninstall.stdout
    payload = json.loads(json_uninstall.stdout)
    assert payload["status"] == "not_installed"
    assert expected_removed_path in payload["removed_files"]
    assert (
        f"{source_entry} init {adapter} --workdir {shlex.quote(str(json_workdir.resolve()))}"
        in payload["next_commands"]["reinstall"]
    )
    assert f"loopora init {adapter} --workdir {shlex.quote(str(json_workdir.resolve()))}" in payload["next_commands"]["reinstall"]
    assert [item["kind"] for item in payload["next_actions"]] == ["reinstall_agent_entry", "refresh_agent_host"]
    assert payload["next_actions"][0]["command"] == payload["next_commands"]["reinstall"]
    assert "Reinstall later:" in payload["next_steps"][0]


def test_cli_adapter_uninstall_keeps_remove_failures_without_low_level_details(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    runner = CliRunner()
    target = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    local_path = tmp_path / "private" / "SKILL.md"
    original_unlink = Path.unlink

    install = runner.invoke(cli.app, ["init", "codex", "--workdir", str(workdir), "--json"])
    assert install.exit_code == 0, install.stdout

    def fail_target_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path == target:
            raise OSError(f"permission denied: {local_path}")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_target_unlink)

    plain = runner.invoke(cli.app, ["uninstall", "codex", "--workdir", str(workdir)])

    assert plain.exit_code == 0, plain.stdout
    assert "kept files: 1 need manual review" in plain.stdout
    assert ".agents/skills/loopora-plan/SKILL.md: remove_failed" in plain.stdout
    assert str(target) not in plain.stdout
    assert str(local_path) not in plain.stdout
    assert "permission denied" not in plain.stdout

    structured = runner.invoke(cli.app, ["uninstall", "codex", "--workdir", str(workdir), "--json"])

    assert structured.exit_code == 0, structured.stdout
    payload = json.loads(structured.stdout)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert {"path": ".agents/skills/loopora-plan/SKILL.md", "reason": "remove_failed"} in payload["kept_files"]
    assert str(target) not in encoded
    assert str(local_path) not in encoded
    assert "permission denied" not in encoded
