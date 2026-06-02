from __future__ import annotations

from compacted_agent_native_support import (
    adapter_entry_paths_text,
    assert_first_task_message_example,
    assert_native_surface_payload,
    assert_native_surface_plain_output,
)
from agent_adapter_test_support import (
    CliRunner,
    Path,
    _assert_loopora_cli_command,
    cli,
    json,
    pytest,
)


@pytest.mark.parametrize(
    ("adapter", "label"),
    [
        ("codex", "Codex"),
        ("claude", "Claude Code"),
        ("opencode", "OpenCode"),
    ],
)
def test_cli_adapter_install_human_output_points_to_agent_next_steps(tmp_path: Path, adapter: str, label: str) -> None:
    workdir = tmp_path / adapter
    workdir.mkdir()
    runner = CliRunner()
    entry_paths = adapter_entry_paths_text(adapter)

    result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir)])

    assert result.exit_code == 0, result.stdout
    assert f"{label} Loopora entry is installed" in result.stdout
    assert f"target project: {workdir.resolve()}" in result.stdout
    assert "next:" in result.stdout
    assert f"Return to {label} in this project" in result.stdout
    assert "task goal, fake-done risk, and required evidence" in result.stdout
    assert "/loopora-plan" in result.stdout
    assert "READY Loop preview" in result.stdout
    assert "/loopora-run" in result.stdout
    assert "same Agent session" in result.stdout
    assert "If /loopora-plan or /loopora-run is not visible" in result.stdout
    assert entry_paths in result.stdout
    assert f"refresh or restart {label}" in result.stdout
    assert "observe evidence, gaps, and verdicts" in result.stdout
    assert "first task message example:" in result.stdout
    assert "diagnostics:" in result.stdout
    assert "- verify install:" in result.stdout
    assert f"loopora init {adapter} --workdir {workdir.resolve()} --check" in result.stdout
    assert "- agent-runtime check:" in result.stdout
    assert f"loopora agent {adapter} check --workdir {workdir.resolve()}" in result.stdout
    assert_native_surface_plain_output(result.stdout)
    if adapter == "claude":
        assert "hooks=claude_session_context_hook" in result.stdout
    else:
        assert "hooks=claude_session_context_hook" not in result.stdout
    assert "managed files:" in result.stdout
    assert result.stdout.index("next:") < result.stdout.index("managed files:")
    assert result.stdout.index("diagnostics:") < result.stdout.index("managed files:")
    assert "adapter installed" not in result.stdout
    assert "YAML bundle" not in result.stdout
    assert_first_task_message_example(result.stdout)

    json_result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])

    assert json_result.exit_code == 0, json_result.stdout
    payload = json.loads(json_result.stdout)
    assert any(f"Return to {label}" in item for item in payload["next_steps"])
    assert any("/loopora-plan" in item for item in payload["next_steps"])
    assert any("/loopora-run" in item for item in payload["next_steps"])
    assert any(entry_paths in item for item in payload["next_steps"])
    assert any(f"refresh or restart {label}" in item for item in payload["next_steps"])
    assert_first_task_message_example(payload["first_task_message_example"])
    assert payload["next_commands"]["plan"] == "/loopora-plan"
    assert payload["next_commands"]["run"] == "/loopora-run"
    assert_native_surface_payload(payload, adapter=adapter, entry_paths=entry_paths)
    _assert_loopora_cli_command(
        payload["next_commands"]["check"],
        f"loopora init {adapter} --workdir {workdir.resolve()} --check",
    )
    _assert_loopora_cli_command(
        payload["next_commands"]["agent_check"],
        f"loopora agent {adapter} check --workdir {workdir.resolve()}",
    )
