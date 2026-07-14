from __future__ import annotations

import sqlite3

from agent_native_v3_helpers import assert_agent_v3_compact_envelope, assert_agent_v3_envelope
from agent_adapter_test_common import _assert_loopora_serve_command
from agent_adapter_test_support import (
    CliRunner,
    Path,
    RunArtifactLayout,
    _assert_agent_native_cli_output,
    _assert_agent_run_json_summary_reports_missing_dispatch,
    _assert_agent_run_summary_continuation,
    _write_agent_native_cli_contract,
    cli,
    json,
    pytest,
)
from loopora.branding import APP_HOME_ENV
from loopora.cli_agent_result_files import RESULT_FILE_MISSING_ERROR, RESULT_FILE_UNREADABLE_ERROR
from loopora.db_schema_v3 import CURRENT_SCHEMA_VERSION
from loopora.service import LooporaError


def test_cli_agent_native_runtime_rejects_future_app_db_as_app_state_recovery(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home"
    workdir = tmp_path / "project"
    result_file = tmp_path / "result.json"
    workdir.mkdir()
    result_file.write_text(json.dumps({"result": {"summary": "ready"}}), encoding="utf-8")
    app_home.mkdir()
    with sqlite3.connect(app_home / "app.db") as connection:
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1}")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))

    runner = CliRunner()
    for args in (
        ["agent", "codex", "plan", "--workdir", str(workdir), "--message", "Ship a safer recovery", "--json"],
        ["agent", "codex", "run", "--workdir", str(workdir), "--json"],
        ["agent", "codex", "next", "--workdir", str(workdir), "--run-id", "run_missing", "--json"],
        ["agent", "codex", "submit", "--result-file", str(result_file), "--workdir", str(workdir), "--json"],
    ):
        result = runner.invoke(cli.app, args)
        payload = json.loads(result.stdout)

        assert result.exit_code == 1
        assert payload["loop_recovery"] == "use_matching_loopora_version_or_reset"
        assert payload["status"] == "blocked_by_app_state"
        assert payload["app_state_status"] == "future_version"
        expected_actions = [
            "use_matching_loopora_version_or_reset",
            "inspect_app_state",
            "create_recovery_archive",
            "preview_app_database_reset",
        ]
        assert (
            payload["app_state_recovery_summary"]["next_action_kinds"],
            payload["next_action_ready_now_kinds"],
            payload["app_state_recovery_summary"]["next_action_ready_after_actions"],
        ) == (
            expected_actions,
            expected_actions[:2],
            {
                "create_recovery_archive": "inspect_app_state",
                "preview_app_database_reset": "create_recovery_archive",
            },
        )
        assert f"loopora doctor --workdir {workdir}" in payload["next_actions"][1]["command"]
        assert f"loopora recovery create --workdir {workdir}" in payload["next_actions"][2]["command"]
        assert f"loopora dev reset --scope app --workdir {workdir}" in payload["next_actions"][3]["command"]
        assert result.stderr == ""


def test_cli_agent_native_plain_runtime_rejects_future_app_db_without_traceback(monkeypatch, tmp_path: Path) -> None:
    app_home = tmp_path / "loopora-home with spaces"
    workdir = tmp_path / "project with spaces"
    result_file = tmp_path / "result.json"
    workdir.mkdir()
    result_file.write_text(json.dumps({"result": {"summary": "ready"}}), encoding="utf-8")
    app_home.mkdir()
    with sqlite3.connect(app_home / "app.db") as connection:
        connection.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION + 1}")
    monkeypatch.setenv(APP_HOME_ENV, str(app_home))

    runner = CliRunner()
    for args in (
        ["agent", "codex", "plan", "--workdir", str(workdir), "--message", "Ship a safer recovery"],
        ["agent", "codex", "run", "--workdir", str(workdir)],
        ["agent", "codex", "next", "--workdir", str(workdir), "--run-id", "run_missing"],
        ["agent", "codex", "submit", "--result-file", str(result_file), "--workdir", str(workdir)],
    ):
        result = runner.invoke(cli.app, args)

        assert result.exit_code == 1
        assert result.stdout == ""
        assert "loop_recovery: use_matching_loopora_version_or_reset" in result.stderr
        assert f"loopora doctor --workdir '{workdir}'" in result.stderr
        assert f"loopora dev reset --scope app --workdir '{workdir}'" in result.stderr
        assert "reset apply after review:" in result.stderr
        assert str(app_home) in result.stderr
        assert "Traceback" not in result.output


def test_cli_agent_submit_recovers_missing_result_file_before_service(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()

    def fail_service():
        raise AssertionError("missing result-file recovery must not open service")

    monkeypatch.setattr(cli, "create_service", fail_service)
    runner = CliRunner()

    plain = runner.invoke(cli.app, ["agent", "codex", "submit", "--workdir", str(workdir)])
    assert plain.exit_code == 1
    assert "Missing option" not in plain.output
    assert "Usage:" not in plain.output
    assert "codex Loopora Agent submit is blocked" in plain.stdout
    assert "result file required" in plain.stdout
    assert "loopora agent codex next --workdir" in plain.stdout
    assert "loopora agent codex submit --result-file <result-file>" in plain.stdout

    result = runner.invoke(cli.app, ["agent", "codex", "submit", "--workdir", str(workdir), "--json"])
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload,
        kind="agent_recovery",
        status="blocked",
        summary_key="agent_submit_result_file_recovery_summary",
    )
    assert result.exit_code == 1
    assert summary["loop_recovery"] == "result_file_required"
    assert summary["status"] == "blocked_by_missing_result_file"
    assert summary["required_identifier"] == "result_file"
    assert summary["next_action_kinds"] == [
        "claim_current_step",
        "fill_result_template",
        "retry_submit_after_result_file",
    ]
    assert summary["next_action_ready_now_kinds"] == ["claim_current_step"]
    assert summary["next_action_ready_after_actions"] == {
        "fill_result_template": "claim_current_step",
        "retry_submit_after_result_file": "fill_result_template",
    }
    assert "loopora agent codex next --workdir" in summary["next_actions"][0]["command"]
    assert "--json" in summary["next_actions"][0]["command"]
    assert summary["next_actions"][1]["after_action"] == "claim_current_step"
    assert "loopora agent codex submit --result-file <result-file>" in summary["next_actions"][2]["command_template"]
    assert summary["next_actions"][2]["after_action"] == "fill_result_template"

    compact = runner.invoke(cli.app, ["agent", "codex", "submit", "--workdir", str(workdir), "--compact-json"])
    compact_summary = assert_agent_v3_compact_envelope(
        json.loads(compact.stdout),
        kind="agent_recovery",
        status="blocked",
        summary_key="agent_submit_result_file_recovery_summary",
    )
    assert compact.exit_code == 1
    assert compact_summary["loop_recovery"] == "result_file_required"
    assert compact_summary["next_action_ready_now_kinds"] == ["claim_current_step"]
    assert "--compact-json" in compact_summary["next_actions"][0]["command"]


def _assert_agent_submit_result_file_repair(result, *, result_file: Path, expected_focus: str) -> None:
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    summary, _legacy = assert_agent_v3_envelope(
        payload,
        kind="agent_submit_repair",
        status="blocked",
        summary_key="agent_submit_repair_summary",
    )
    assert summary["submit_repair"] == "repair_result_json"
    assert summary["result_file_to_repair"] == str(result_file)
    assert expected_focus in " ".join(summary["repair_focus"])
    assert result.stderr == ""


def test_cli_agent_submit_repairs_unreadable_result_file_before_service(monkeypatch, tmp_path: Path) -> None:
    workdir = tmp_path / "project"
    workdir.mkdir()
    missing_result = workdir / "missing.result.json"
    directory_result = workdir / "result-as-directory.json"
    directory_result.mkdir()

    def fail_service():
        raise LooporaError("local App state is unavailable")

    monkeypatch.setattr(cli, "create_service", fail_service)
    runner = CliRunner()

    missing = runner.invoke(
        cli.app,
        ["agent", "codex", "submit", "--result-file", str(missing_result), "--workdir", str(workdir), "--json"],
    )
    directory = runner.invoke(
        cli.app,
        ["agent", "codex", "submit", "--result-file", str(directory_result), "--workdir", str(workdir), "--json"],
    )

    _assert_agent_submit_result_file_repair(
        missing,
        result_file=missing_result,
        expected_focus="create the filled result JSON file",
    )
    _assert_agent_submit_result_file_repair(
        directory,
        result_file=directory_result,
        expected_focus="make result_file_to_repair readable as UTF-8 JSON",
    )
    assert RESULT_FILE_MISSING_ERROR in missing.output
    assert RESULT_FILE_UNREADABLE_ERROR in directory.output
    assert "use_matching_loopora_version_or_reset" not in missing.output + directory.output
    assert "local App state is unavailable" not in missing.output + directory.output


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
                "agent_run_summary": {
                    "schema_version": 3,
                    "run_id": "run_agent",
                    "run_status": "awaiting_agent",
                    "started_new_run": True,
                    "complete": False,
                    "native_todo": {"items": ["full summary detail must not leak into compact output"]},
                    "native_trace_contract": {"purpose": "full summary diagnostics only"},
                },
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
                    "coverage_target_ids": ["done_when.check_001", "gatekeeper.finish"],
                    "coverage_targets": [
                        {
                            "id": "done_when.check_001",
                            "kind": "done_when",
                            "required": True,
                            "text": "Support admin can approve a refund.",
                        },
                        {
                            "id": "gatekeeper.finish",
                            "kind": "gatekeeper",
                            "required": True,
                            "text": "GateKeeper needs supporting evidence refs.",
                        },
                    ],
                    "continuation": {
                        "active": True,
                        "previous_run_id": "run_previous",
                        "previous_task_verdict": {"status": "insufficient_evidence"},
                        "coverage": {"covered_check_count": 1, "missing_check_count": 2},
                        "next_focus": ["done_when.check_001: Support admin path still lacks direct proof."],
                    },
                    "known_evidence_count": 3,
                    "context_absolute_path": str(run_dir / "iterations" / "iter_000" / "steps" / "00__builder_step" / "step_instruction_context.json"),
                    "step_contract_absolute_path": str(layout.step_contract_path(0, 0, "builder_step")),
                    "submit_hint": {
                        "command": "loopora agent codex submit --run-id run_agent --step-id builder_step",
                        "result_file_contract": "Result file must contain one wrapper JSON object with loopora_host_dispatch and a schema-shaped result; replace null placeholders before submit.",
                        "result_template_absolute_path": str(workdir / ".loopora" / "agent_outbox" / "codex" / "run_agent__builder_step.result.template.json"),
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
    _assert_agent_native_cli_output(result.stdout, layout, workdir=workdir, adapter=adapter, loopora_home=loopora_home)

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
    summary, _legacy = assert_agent_v3_envelope(payload, kind="agent_run", summary_key="agent_run_summary")
    assert summary["next_role_dispatch_message"] == summary["next_step"]["role_dispatch_message"]
    _assert_compact_role_dispatch_message(summary["next_role_dispatch_message"], target_agent="loopora-builder")
    summary_keys = list(summary)
    assert summary_keys.index("agent_work_panel") < summary_keys.index("agent_surface")
    continuation_summary = _assert_agent_run_summary_continuation(
        summary,
        previous_run_id="run_previous",
        previous_task_verdict_status="insufficient_evidence",
        missing_required_check_count=2,
    )
    assert continuation_summary["next_focus"] == ["done_when.check_001: Support admin path still lacks direct proof."]

    compact_result = runner.invoke(
        cli.app,
        [
            "agent",
            adapter,
            "run",
            "--workdir",
            str(workdir),
            "--context-id",
            "thread-1",
            "--no-web",
            "--json",
            "--compact-json",
        ],
    )

    _assert_compact_agent_run_handoff(
        compact_result,
        workdir=workdir,
        loopora_home=loopora_home,
    )


def _assert_compact_agent_run_handoff(compact_result, *, workdir: Path, loopora_home: Path) -> None:
    assert compact_result.exit_code == 0, compact_result.stdout
    compact_payload = json.loads(compact_result.stdout)
    compact_summary = assert_agent_v3_compact_envelope(
        compact_payload,
        kind="agent_run",
        summary_key="agent_run_summary",
    )
    assert len(compact_result.stdout.encode("utf-8")) < 10_000
    assert compact_summary["run_url"] == "/runs/run_agent"
    assert compact_summary["run_url_status"] == "relative_path_web_not_started"
    _assert_loopora_serve_command(
        compact_summary["run_url_web_start_command"],
        workdir=workdir,
        loopora_home=loopora_home,
    )
    assert compact_summary["next_step"]["coverage_target_ids"] == ["done_when.check_001", "gatekeeper.finish"]
    assert "native_todo" not in compact_summary
    assert "native_trace_contract" not in compact_summary
    panel = compact_summary["agent_work_panel"]
    assert panel["target_agent"] == "loopora-builder"
    assert panel["role_handoff_status"] == "blocked_before_dispatch"
    assert panel["role_handoff_owner"] == "current_host_agent"
    assert panel["evidence_focus"] == "done_when.check_001: Support admin path still lacks direct proof."
    assert panel["top_gaps"][0]["target_id"] == "done_when.check_001"
    assert "todo_items" not in panel
    compact_summary_keys = list(compact_summary)
    assert compact_summary_keys.index("agent_work_panel") < compact_summary_keys.index("agent_surface")
    assert compact_payload["technical_handoff"]["next_step_contract_path"].endswith("step_contract.json")
    assert compact_payload["technical_handoff"]["run_url_status"] == "relative_path_web_not_started"
    assert "next_role_dispatch_message" not in compact_payload["technical_handoff"]
    _assert_compact_role_dispatch_message(compact_summary["next_role_dispatch_message"], target_agent="loopora-builder")


def _assert_compact_role_dispatch_message(message: str, *, target_agent: str) -> None:
    assert f"target_agent={target_agent}" in message
    assert "context_path=" in message
    assert "step_contract_path=" in message
    assert "result_template=" in message
    assert "coverage_target_ids=done_when.check_001, gatekeeper.finish" in message
    assert "Use this exact string as the whole Agent/Task prompt" in message
    assert "prepend `You are running as`" in message
    assert "append `Do the following`" in message
    assert "return one raw wrapper JSON object only" in message
    assert "Do not paste full CLI JSON" in message
