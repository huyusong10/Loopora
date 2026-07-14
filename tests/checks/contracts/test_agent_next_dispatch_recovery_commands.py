from __future__ import annotations

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix
from loopora import cli
from loopora import cli_agent_runtime_commands

from agent_adapter_test_support import (
    Path,
    _assert_codex_native_surface_summary,
    _assert_loopora_cli_command,
    cli_agent_adapter_commands,
)


def test_agent_next_summary_reports_dispatch_recovery_commands_when_target_config_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    home = tmp_path / "loopora home"
    workdir = tmp_path / "project"
    monkeypatch.setenv("LOOPORA_HOME", str(home))
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = agent_adapter_command_prefix.current_project_file_loopora_cli_entry()

    summary = cli_agent_adapter_commands._agent_next_summary(
        {
            "adapter": "codex",
            "workdir": str(workdir),
            "run": {"id": "run_next", "status": "awaiting_agent", "workdir": str(workdir)},
            "next_step": {
                "adapter": "codex",
                "step_id": "contract_inspection_step",
                "role": {"name": "Contract Inspector"},
                "role_dispatch": {
                    "target_agent": "loopora-inspector",
                    "target_agent_config_absolute_path": str(workdir / ".codex" / "agents" / "loopora-inspector.toml"),
                    "target_agent_config_exists": False,
                },
            },
        }
    )

    next_step = summary["next_step"]
    _assert_codex_native_surface_summary(summary)
    assert "dispatch_next" not in next_step
    assert next_step["target_agent_config_exists"] is False
    dispatch_unavailable = next_step["dispatch_unavailable"]
    assert dispatch_unavailable["reason"] == "target_agent_config_missing"
    assert dispatch_unavailable["target_agent"] == "loopora-inspector"
    assert f"{source_entry} agent codex check" in dispatch_unavailable["check_command"]
    assert f"{source_entry} init codex" in dispatch_unavailable["repair_command"]
    _assert_loopora_cli_command(
        dispatch_unavailable["check_command"],
        f"loopora agent codex check --workdir {workdir}",
        loopora_home=home,
    )
    _assert_loopora_cli_command(
        dispatch_unavailable["repair_command"],
        f"loopora init codex --workdir {workdir}",
        loopora_home=home,
    )
    assert "do not submit inline role work" in dispatch_unavailable["next"]


def test_agent_next_accepts_step_id_as_compatibility_noop(monkeypatch, tmp_path: Path) -> None:
    captured = {}

    def fake_claim_agent_next_from_cli(request) -> None:
        captured["adapter"] = request.adapter
        captured["run_id"] = request.run_id
        captured["json_output"] = request.json_output

    monkeypatch.setattr(cli_agent_runtime_commands, "claim_agent_next_from_cli", fake_claim_agent_next_from_cli)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "agent",
            "claude",
            "next",
            "--workdir",
            str(tmp_path),
            "--run-id",
            "run_example",
            "--step-id",
            "inspector_step",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured == {"adapter": "claude", "run_id": "run_example", "json_output": True}


def test_agent_next_help_names_step_id_as_compatibility_noop() -> None:
    runner = CliRunner()

    result = runner.invoke(cli.app, ["agent", "claude", "next", "--help"])

    assert result.exit_code == 0, result.output
    assert "--step-id" in result.stdout
    assert "Compatibility no-op" in result.stdout
    assert "active step" in result.stdout
