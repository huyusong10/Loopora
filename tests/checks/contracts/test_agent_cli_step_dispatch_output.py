from __future__ import annotations

from agent_adapter_test_support import Path, cli_agent_adapter_commands


def test_agent_cli_current_step_prints_target_agent_config_availability(capsys, tmp_path: Path) -> None:
    config_path = tmp_path / ".codex" / "agents" / "loopora-builder.toml"
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "builder_step",
            "iter": 0,
            "step_order": 0,
            "role": {"name": "Builder"},
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "target_agent_config_absolute_path": str(config_path),
                "target_agent_config_exists": True,
            },
            "action_policy": {"workspace": "workspace_write", "can_block": False, "can_finish_run": False},
            "required_coverage": {"status": "pending", "covered_check_count": 0, "missing_check_count": 2, "top_gaps": []},
            "known_evidence_ids": [],
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out

    assert f"next_target_agent_config: {config_path}" in output
    assert "next_target_agent_config_exists: true" in output
    assert "dispatch_next: invoke loopora-builder" in output
    assert "dispatch_unavailable:" not in output
