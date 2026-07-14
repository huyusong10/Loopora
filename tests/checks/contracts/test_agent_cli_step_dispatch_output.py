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

    assert f"next_target_agent_config: {config_path}" not in output
    assert "next_target_agent_config_exists: true" in output
    assert "dispatch_next: invoke loopora-builder" in output
    assert "dispatch_unavailable:" not in output


def test_agent_cli_current_step_dispatch_repair_uses_artifact_workdir(capsys, tmp_path: Path) -> None:
    workdir = tmp_path / "project with spaces"
    config_path = workdir / ".codex" / "agents" / "loopora-builder.toml"
    context_path = workdir / ".loopora" / "runs" / "run_1" / "steps" / "builder" / "context.json"
    template_path = workdir / ".loopora" / "agent_outbox" / "codex" / "builder.result.template.json"
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "builder_step",
            "role": {"name": "Builder"},
            "context_absolute_path": str(context_path),
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "target_agent_config_absolute_path": str(config_path),
                "target_agent_config_exists": False,
            },
            "submit_hint": {"result_template_absolute_path": str(template_path)},
        }
    )

    output = capsys.readouterr().out

    assert "dispatch_unavailable: loopora-builder config is missing;" in output
    assert f"next_target_agent_config: {config_path}" in output
    assert f"loopora agent codex check --workdir '{workdir}'" in output
    assert f"loopora init codex --workdir '{workdir}'" in output
    assert 'loopora agent codex check --workdir "$PWD"' not in output


def test_agent_cli_current_step_dispatch_repair_requires_workdir_context(capsys) -> None:
    cli_agent_adapter_commands._print_agent_current_step(
        {
            "step_id": "builder_step",
            "role": {"name": "Builder"},
            "role_dispatch": {
                "target_agent": "loopora-builder",
                "target_agent_config_exists": False,
            },
            "submit_hint": {},
        }
    )

    output = capsys.readouterr().out

    assert "dispatch_unavailable: loopora-builder config is missing;" in output
    assert "Recover the project workdir before repairing the managed role agent config." in output
    assert 'loopora agent codex check --workdir "$PWD"' not in output
    assert "loopora init codex" not in output
