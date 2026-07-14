from __future__ import annotations

import json
import os
import shlex
import sqlite3
from pathlib import Path

from cli_run_output_test_support import print_run_result_output
from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli, existing_work_status
from loopora.branding import APP_HOME_ENV
from loopora.cli_run_output import loop_create_result_payload, run_result_payload
from loopora.run_worker_start import BACKGROUND_WORKER_START_ERROR
from loopora.service import create_service


def test_cli_run_result_separates_run_status_and_task_verdict(capsys, tmp_path: Path) -> None:
    output = print_run_result_output(
        capsys,
        {
            "id": "run_contract",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_contract"),
            "task_verdict": {
                "status": "insufficient_evidence",
                "source": "rounds_completion",
                "summary": "The run ended, but evidence is still too thin.",
            },
        },
    )

    assert "run_status: succeeded" in output
    assert "task_verdict: insufficient_evidence" in output
    assert "task_verdict_source: rounds_completion" in output
    assert "task_verdict_summary: The run ended, but evidence is still too thin." in output


def test_cli_run_result_explains_passing_verdict_audit_buckets(capsys, tmp_path: Path) -> None:
    output = print_run_result_output(
        capsys,
        {
            "id": "run_passed_with_audit_buckets",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_passed_with_audit_buckets"),
            "task_verdict": {
                "status": "passed",
                "source": "gatekeeper",
                "summary": "Required evidence passed.",
                "buckets": {
                    "proven": [{"id": "done_when.check_001", "label": "Required proof", "required": True}],
                    "weak": [{"label": "Earlier weak evidence remains visible."}],
                    "unproven": [{"id": "fake_done.risk_001", "label": "Advisory fake-done risk", "required": False}],
                    "blocking": [],
                    "residual_risk": [{"label": "Tracked follow-up.", "managed": True}],
                },
            },
        },
    )

    assert "task_verdict: passed" in output
    assert "task_verdict_buckets: proven 1 / weak 1 / unproven 1 / blocking 0 / residual_risk 1" in output
    assert "task_verdict_required_basis: 1/1 required targets proven; blocking 0" in output
    assert "task_verdict_bucket_note: passing verdict kept non-blocking" in output
    assert "for audit or accepted follow-up" in output
    assert "required coverage and GateKeeper support still passed" in output


def test_cli_run_result_prints_not_evaluated_when_task_verdict_is_missing(capsys, tmp_path: Path) -> None:
    output = print_run_result_output(
        capsys,
        {
            "id": "run_legacy",
            "status": "succeeded",
            "run_status": "succeeded",
            "runs_dir": str(tmp_path / "runs" / "run_legacy"),
        },
    )

    assert "run_status: succeeded" in output
    assert "task_verdict: not_evaluated" in output


def test_cli_run_result_surfaces_lifecycle_failure_recovery_before_task_verdict(capsys, tmp_path: Path) -> None:
    output = print_run_result_output(
        capsys,
        {
            "id": "run_start_failed",
            "loop_id": "loop_start_failed",
            "status": "failed",
            "run_status": "failed",
            "error_message": BACKGROUND_WORKER_START_ERROR,
            "runs_dir": str(tmp_path / "runs" / "run_start_failed"),
            "task_verdict": {
                "status": "not_evaluated",
                "source": "run_status",
                "summary": "No recordable evidence was produced.",
            },
        },
    )

    assert "run_status: failed" in output
    assert "run_status_label: run_start_failed" in output
    assert "run_recovery: retry_run_start" in output
    assert _loopora_command_tokens(_run_recovery_command(output)) == ["loopora", "loops", "rerun", "loop_start_failed"]
    assert output.index("run_recovery: retry_run_start") < output.index("task_verdict: not_evaluated")


def test_cli_run_result_json_payload_surfaces_lifecycle_failure_recovery(tmp_path: Path) -> None:
    run = {
        "id": "run_start_failed",
        "loop_id": "loop_start_failed",
        "status": "failed",
        "run_status": "failed",
        "error_message": BACKGROUND_WORKER_START_ERROR,
        "runs_dir": str(tmp_path / "runs" / "run_start_failed"),
        "task_verdict": {"status": "not_evaluated", "source": "run_status"},
    }

    payload = run_result_payload(run, json_output=True)

    assert "run_recovery" not in run
    assert payload["status_label"] == "run_start_failed"
    assert payload["run_recovery"] == "retry_run_start"
    action = payload["next_actions"][0]
    assert action["kind"] == "retry_run_start"
    assert _loopora_command_tokens(action["command"]) == [
        "loopora",
        "loops",
        "rerun",
        "loop_start_failed",
        "--json",
    ]
    created_payload = loop_create_result_payload({"id": "loop_start_failed"}, run)
    assert created_payload["run"]["run_recovery"] == "retry_run_start"


def test_cli_run_result_recovery_commands_preserve_source_checkout_entry(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()
    run = {
        "id": "run_start_failed",
        "loop_id": "loop_start_failed",
        "status": "failed",
        "run_status": "failed",
        "error_message": BACKGROUND_WORKER_START_ERROR,
        "runs_dir": str(tmp_path / "runs" / "run_start_failed"),
        "task_verdict": {"status": "not_evaluated", "source": "run_status"},
    }

    output = print_run_result_output(capsys, run)
    payload = run_result_payload(run, json_output=True)

    assert _loopora_command_tokens(_run_recovery_command(output)) == shlex.split(
        f"{source_entry} loops rerun loop_start_failed"
    )
    assert _loopora_command_tokens(payload["next_actions"][0]["command"]) == shlex.split(
        f"{source_entry} loops rerun loop_start_failed --json"
    )


def test_cli_run_result_recovery_commands_preserve_loop_id_argument(capsys, tmp_path: Path) -> None:
    unsafe_loop_id = "loop start failed;with $chars"
    run = {
        "id": "run_start_failed",
        "loop_id": unsafe_loop_id,
        "status": "failed",
        "run_status": "failed",
        "error_message": BACKGROUND_WORKER_START_ERROR,
        "runs_dir": str(tmp_path / "runs" / "run_start_failed"),
        "task_verdict": {"status": "not_evaluated", "source": "run_status"},
    }

    output = print_run_result_output(capsys, run)
    assert _loopora_command_tokens(_run_recovery_command(output)) == ["loopora", "loops", "rerun", unsafe_loop_id]

    payload = run_result_payload(run, json_output=True)
    action = payload["next_actions"][0]
    assert action["kind"] == "retry_run_start"
    assert _loopora_command_tokens(action["command"]) == ["loopora", "loops", "rerun", unsafe_loop_id, "--json"]


def test_project_status_combines_planning_runs_and_saved_work(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    home.mkdir()
    (home / "app.db").touch()
    scopes: list[str] = []

    def fake_home_sections(
        _service,
        *,
        workdir_context: str = "",
        reconcile_orphans: bool = True,
    ) -> dict[str, list[dict]]:
        assert reconcile_orphans is False
        scopes.append(workdir_context)
        return _existing_work_sections(project)

    monkeypatch.setenv(APP_HOME_ENV, str(home))
    monkeypatch.setattr(cli, "create_service", lambda **_kwargs: object())
    monkeypatch.setattr(existing_work_status, "home_loop_sections", fake_home_sections)
    result = CliRunner().invoke(
        cli.app,
        ["status", "--workdir", str(project), "--language", "zh"],
    )

    assert result.exit_code == 0, result.stdout
    assert scopes == [str(project.resolve())]
    assert "待处理：1 · 最近：1 · 已保存未运行：1" in result.stdout
    assert "[interrupted] 恢复发布规划" in result.stdout
    assert "本地规划进程已中断" in result.stdout
    assert "继续规划" in result.stdout
    assert "loopora serve --open" in result.stdout
    assert "只读：未启动或修改任何工作。" in result.stdout


def test_project_status_json_all_projects_keeps_complete_compact_projection(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    home.mkdir()
    (home / "app.db").touch()
    scopes: list[str] = []

    def fake_home_sections(
        _service,
        *,
        workdir_context: str = "",
        reconcile_orphans: bool = True,
    ) -> dict[str, list[dict]]:
        assert reconcile_orphans is False
        scopes.append(workdir_context)
        return _existing_work_sections(project)

    monkeypatch.setenv(APP_HOME_ENV, str(home))
    monkeypatch.setattr(cli, "create_service", lambda **_kwargs: object())
    monkeypatch.setattr(existing_work_status, "home_loop_sections", fake_home_sections)
    result = CliRunner().invoke(cli.app, ["status", "--all", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert scopes == [""]
    assert payload["schema_version"] == 2
    assert payload["scope"] == "all_projects"
    assert payload["read_only"] is True
    assert payload["counts"] == {
        "needs_attention": 1,
        "recent": 1,
        "saved_not_run": 1,
        "saved_loops": 2,
    }
    assert payload["primary_item"]["source_kind"] == "alignment_session"
    assert payload["primary_item"]["status"] == "interrupted"
    assert payload["primary_item"]["next_actions"][0]["kind"] == "open_existing_work"
    assert "--open-path" in payload["next_actions"][0]["command"]
    assert payload["recent"][0]["latest_run_id"] == "run_recent"
    assert payload["saved_not_run"][0]["id"] == "loop_saved"


def test_project_status_empty_app_home_does_not_create_storage(monkeypatch, tmp_path: Path) -> None:
    home, project = tmp_path / "missing-home", tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv(APP_HOME_ENV, str(home))

    result = CliRunner().invoke(cli.app, ["status", "--workdir", str(project), "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert (payload["status"], payload["read_only"], payload["runtime_reconciliation"]["status"]) == (
        "empty",
        True,
        "not_needed",
    )
    assert not home.exists()


def test_project_status_is_no_write_until_scoped_runtime_reconciliation_is_explicit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    first_project, second_project, live_project = tmp_path / "first", tmp_path / "second", tmp_path / "live"
    first_project.mkdir()
    second_project.mkdir()
    live_project.mkdir()
    spec = tmp_path / "spec.md"
    spec.write_text(_status_test_spec(), encoding="utf-8")
    monkeypatch.setenv(APP_HOME_ENV, str(home))
    service = create_service()
    first_run = _create_stale_status_run(service, first_project, spec, name="First stale run")
    second_run = _create_stale_status_run(service, second_project, spec, name="Second stale run")
    live_run = _create_stale_status_run(service, live_project, spec, name="Live run", runner_pid=os.getpid())
    first_session = _create_stale_status_alignment(service, first_project, session_id="align_first")
    second_session = _create_stale_status_alignment(service, second_project, session_id="align_second")
    app_state_before_observation = _app_state_snapshot(home)

    observed_plain = CliRunner().invoke(cli.app, ["status", "--workdir", str(first_project)])
    observed = CliRunner().invoke(cli.app, ["status", "--workdir", str(first_project), "--json"])
    observed_payload = json.loads(observed.stdout)

    assert observed.exit_code == 0, observed.stdout
    assert "Runtime reconciliation required: 1 stale Run(s), 1 orphaned planning session(s)" in observed_plain.stdout
    assert f"status --workdir {first_project.resolve()} --reconcile" in observed_plain.stdout
    assert _app_state_snapshot(home) == app_state_before_observation
    assert service.repository.get_run(first_run["id"])["status"] == "running"
    assert service.repository.get_run(second_run["id"])["status"] == "running"
    assert service.repository.get_run(live_run["id"])["status"] == "running"
    assert service.repository.get_alignment_session(first_session["id"])["status"] == "running"
    assert service.repository.get_alignment_session(second_session["id"])["status"] == "running"
    assert observed_payload["read_only"] is True
    assert observed_payload["runtime_reconciliation"]["status"] == "required"
    assert observed_payload["runtime_reconciliation"]["stale_run_count"] == 1
    assert observed_payload["runtime_reconciliation"]["orphaned_planning_session_count"] == 1
    assert observed_payload["next_actions"][0]["kind"] == "reconcile_orphaned_runtime_state"
    assert f"status --workdir {first_project.resolve()} --reconcile" in observed_payload["next_actions"][0]["command"]

    reconciled = CliRunner().invoke(
        cli.app,
        ["status", "--workdir", str(first_project), "--reconcile", "--json"],
    )
    reconciled_payload = json.loads(reconciled.stdout)

    assert reconciled.exit_code == 0, reconciled.stdout
    assert service.repository.get_run(first_run["id"])["status"] == "stopped"
    assert service.repository.get_run(second_run["id"])["status"] == "running"
    assert service.repository.get_alignment_session(first_session["id"])["status"] == "failed"
    assert service.repository.get_alignment_session(second_session["id"])["status"] == "running"
    assert reconciled_payload["read_only"] is False
    assert reconciled_payload["runtime_reconciliation"]["status"] == "applied"
    assert reconciled_payload["runtime_reconciliation"]["reconciled_run_ids"] == [first_run["id"]]
    assert reconciled_payload["runtime_reconciliation"]["reconciled_planning_session_ids"] == [first_session["id"]]

    live_reconcile = CliRunner().invoke(
        cli.app,
        ["status", "--workdir", str(live_project), "--reconcile", "--json"],
    )
    assert live_reconcile.exit_code == 0, live_reconcile.stdout
    assert json.loads(live_reconcile.stdout)["runtime_reconciliation"]["status"] == "not_needed"
    assert service.repository.get_run(live_run["id"])["status"] == "running"


def test_project_status_rejects_ambiguous_scope_before_service_access(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(cli, "create_service", lambda: (_ for _ in ()).throw(AssertionError("service accessed")))

    plain = CliRunner().invoke(cli.app, ["status", "--workdir", str(project), "--all"])
    structured = CliRunner().invoke(cli.app, ["status", "--workdir", str(project), "--all", "--json"])

    assert plain.exit_code == 1
    assert "choose either --workdir or --all" in plain.stderr
    assert structured.exit_code == 1
    assert json.loads(structured.stdout) == {"status": "error", "error": "choose either --workdir or --all, not both"}


def _existing_work_sections(project: Path) -> dict[str, list[dict]]:
    recent = {
        "id": "loop_recent",
        "name": "Recent release run",
        "workdir": str(project),
        "latest_status": "succeeded",
        "latest_run_id": "run_recent",
        "card_href": "/runs/run_recent?workdir=project",
        "card_hint_en": "Task verdict passed.",
        "card_hint_zh": "Loop 裁决已通过。",
    }
    saved = {
        "id": "loop_saved",
        "name": "Saved release plan",
        "workdir": str(project),
        "latest_status": "draft",
        "latest_run_id": "",
        "card_href": "/loops/loop_saved?workdir=project",
        "card_hint_en": "No run yet.",
        "card_hint_zh": "尚未运行。",
    }
    return {
        "active_loops": [
            {
                "id": "align_interrupted",
                "source_kind": "alignment_session",
                "name": "恢复发布规划",
                "workdir": str(project),
                "latest_status": "failed",
                "status_label": "interrupted",
                "card_href": "/loops/new/bundle?alignment_session_id=align_interrupted",
                "attention_reason_kind": "alignment_worker_interrupted",
                "attention_reason_en": "Local planning was interrupted",
                "attention_reason_zh": "本地规划进程已中断",
                "attention_action_kind": "retry_alignment_generation",
                "attention_action_en": "Resume planning",
                "attention_action_zh": "继续规划",
            }
        ],
        "recent_loops": [recent],
        "loops": [recent, saved],
    }


def _create_stale_status_run(
    service,
    project: Path,
    spec: Path,
    *,
    name: str,
    runner_pid: int = 999_999_999,
) -> dict:
    loop = service.create_loop(
        name=name,
        spec_path=spec,
        workdir=project,
        model="",
        reasoning_effort="",
        max_iters=2,
        max_role_retries=1,
        delta_threshold=0.005,
        trigger_window=2,
        regression_window=2,
        role_models={},
    )
    run = service.start_run(loop["id"])
    return service.repository.update_run(
        run["id"],
        status="running",
        runner_pid=runner_pid,
        active_role="builder",
        started_at="2026-04-13T08:00:00+00:00",
    )


def _create_stale_status_alignment(service, project: Path, *, session_id: str) -> dict:
    return service.repository.create_alignment_session(
        {
            "id": session_id,
            "status": "running",
            "workdir": str(project.resolve()),
            "bundle_path": str(project / ".loopora" / "alignment_sessions" / session_id / "candidate.yml"),
            "active_child_pid": 999_999_999,
            "transcript": [{"role": "user", "content": "Preserve this planning task."}],
        }
    )


def _status_test_spec() -> str:
    return """# Task

Recover existing work safely.

# Done When

- Observation and repair stay distinct.

# Guardrails

- Do not mutate during observation.

# Success Surface

- Recovery is explicit and scoped.

# Fake Done

- Read-only output that changes records.

# Evidence Preferences

- Prefer persisted before/after state.

# Residual Risk

Unscoped mutation fails closed.

# Role Notes

## Builder Notes

Preserve the observation boundary.
"""


def _app_state_snapshot(root: Path) -> dict[str, object]:
    database = root / "app.db"
    with sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True) as connection:
        database_dump = tuple(connection.iterdump())
    sqlite_files = {database, database.with_name("app.db-shm"), database.with_name("app.db-wal")}
    files = {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path not in sqlite_files
    }
    return {"database": database_dump, "files": files}


def _run_recovery_command(output: str) -> str:
    return next(
        line.removeprefix("run_recovery_command: ")
        for line in output.splitlines()
        if line.startswith("run_recovery_command: ")
    )


def _loopora_command_tokens(command: str) -> list[str]:
    tokens = shlex.split(command)
    while tokens and "=" in tokens[0] and not tokens[0].startswith("--"):
        tokens = tokens[1:]
    return tokens
