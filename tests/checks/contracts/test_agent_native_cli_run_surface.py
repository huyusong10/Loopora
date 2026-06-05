from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_compact_envelope, assert_agent_v3_envelope
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

    assert compact_result.exit_code == 0, compact_result.stdout
    compact_payload = json.loads(compact_result.stdout)
    compact_summary = assert_agent_v3_compact_envelope(
        compact_payload,
        kind="agent_run",
        summary_key="agent_run_summary",
    )
    assert compact_summary["next_step"]["coverage_target_ids"] == ["done_when.check_001", "gatekeeper.finish"]
    compact_summary_keys = list(compact_summary)
    assert compact_summary_keys.index("agent_work_panel") < compact_summary_keys.index("agent_surface")
    assert compact_payload["technical_handoff"]["next_step_contract_path"].endswith("step_contract.json")
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
