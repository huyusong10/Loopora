from __future__ import annotations

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
