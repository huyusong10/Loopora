from __future__ import annotations

from loopora import agent_adapter_command_prefix

from agent_native_v3_helpers import assert_agent_v3_envelope
from agent_adapter_test_support import (
    CliRunner,
    LooporaConflictError,
    Path,
    _assert_codex_native_surface_summary,
    _assert_labeled_loopora_agent_command,
    _assert_loopora_cli_command,
    _assert_loopora_serve_command,
    _error_text,
    _labeled_value,
    cli,
    json,
)


def test_cli_agent_run_active_workdir_conflict_reports_recovery_commands(sample_workdir: Path, monkeypatch) -> None:
    loopora_home = sample_workdir.parent / "loopora home"
    monkeypatch.setenv("LOOPORA_HOME", str(loopora_home))
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

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
                            sample_workdir
                            / ".loopora"
                            / "agent_outbox"
                            / "codex"
                            / "run_active__builder_step.result.template.json"
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
    summary, _legacy = assert_agent_v3_envelope(
        payload, kind="agent_recovery", summary_key="agent_loop_recovery_summary", status="blocked"
    )
    assert summary["loop_recovery"] == "active_run_conflict"
    _assert_codex_native_surface_summary(summary)
    active_run = summary["active_runs"][0]
    assert summary["active_run_count"] == 1
    assert active_run["id"] == "run_active"
    assert active_run["status"] == "awaiting_agent"
    assert active_run["loop_name"] == "Refund safety Loop"
    assert active_run["current_step"]["step_id"] == "builder_step"
    assert active_run["current_step"]["target_agent"] == "loopora-builder"
    assert summary["active_run_url"] == "/runs/run_active"
    assert summary["active_run_url_status"] == "relative_path_web_not_started"
    _assert_loopora_serve_command(
        summary["active_run_url_web_start_command"],
        workdir=sample_workdir,
        loopora_home=loopora_home,
    )
    assert payload["technical_handoff"]["active_run_url_status"] == "relative_path_web_not_started"
    assert summary["next_active_run_command"].endswith("--run-id run_active --json --compact-json --entry-source codex_project_skill")
    assert f"{source_entry} agent codex next" in summary["next_active_run_command"]
    assert f"{source_entry} loops stop run_active" in summary["stop_active_run_command"]
    assert f"{source_entry} serve" in summary["active_run_url_web_start_command"]
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
    assert summary["message"].endswith("before starting another preview or run")

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
    assert "active_run_url: /runs/run_active" in text_result.stdout
    assert "active_run_url_status: relative_path_web_not_started" in text_result.stdout
    _assert_loopora_serve_command(
        _labeled_value(text_result.stdout, "active_run_url_web_start_command"),
        workdir=sample_workdir,
        loopora_home=loopora_home,
    )
    _assert_labeled_loopora_agent_command(text_result.stdout, "next_active_run_command", "next")
    stop_command = _labeled_value(text_result.stdout, "stop_active_run_command")
    assert f"{source_entry} loops stop run_active" in stop_command
    assert f"{source_entry} serve" in _labeled_value(text_result.stdout, "active_run_url_web_start_command")
    _assert_loopora_cli_command(stop_command, "loopora loops stop run_active", loopora_home=loopora_home)
