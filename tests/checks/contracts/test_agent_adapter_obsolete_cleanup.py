from __future__ import annotations

from agent_adapter_test_support import (
    LooporaConflictError,
    Path,
    agent_adapters,
    json,
    pytest,
)


def test_claude_adapter_removes_obsolete_managed_command_wrappers(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    commands_dir = workdir / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    gen_command = commands_dir / "loopora-plan.md"
    loop_command = commands_dir / "loopora-run.md"
    gen_command.write_text("<!-- LOOPORA-MANAGED: claude-code-adapter old gen -->\n", encoding="utf-8")
    loop_command.write_text("<!-- LOOPORA-MANAGED: claude-code-adapter old loop -->\n", encoding="utf-8")

    result = service.install_agent_adapter("claude", workdir=workdir)

    assert result["status"] == "installed"
    assert result["removed_obsolete_files"] == [
        ".claude/commands/loopora-plan.md",
        ".claude/commands/loopora-run.md",
    ]
    assert not gen_command.exists()
    assert not loop_command.exists()
    manifest = json.loads((workdir / ".loopora" / "adapters" / "claude" / "manifest.json").read_text(encoding="utf-8"))
    assert ".claude/commands/loopora-plan.md" not in {item["path"] for item in manifest["managed_files"]}


def test_claude_adapter_refuses_unowned_obsolete_command_wrappers(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    command = workdir / ".claude" / "commands" / "loopora-plan.md"
    command.parent.mkdir(parents=True)
    command.write_text("# User-owned Claude command\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError, match="obsolete Claude Code adapter files"):
        service.install_agent_adapter("claude", workdir=workdir)

    assert command.read_text(encoding="utf-8") == "# User-owned Claude command\n"
    assert not (workdir / ".loopora" / "adapters" / "claude" / "manifest.json").exists()


@pytest.mark.parametrize(
    ("adapter", "old_paths"),
    [
        (
            "codex",
            [
                ".agents/skills/loopora-gen/SKILL.md",
                ".agents/skills/loopora-loop/SKILL.md",
            ],
        ),
        (
            "claude",
            [
                ".claude/skills/loopora-gen/SKILL.md",
                ".claude/skills/loopora-loop/SKILL.md",
            ],
        ),
        (
            "opencode",
            [
                ".opencode/commands/loopora-gen.md",
                ".opencode/commands/loopora-loop.md",
            ],
        ),
    ],
)
def test_adapter_install_removes_legacy_managed_slash_entries(
    service_factory,
    tmp_path: Path,
    adapter: str,
    old_paths: list[str],
) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / adapter
    workdir.mkdir()
    for relative_path in old_paths:
        target = workdir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        marker = agent_adapters.MANAGED_MARKERS[adapter]
        target.write_text(f"<!-- {marker} legacy slash entry -->\n", encoding="utf-8")

    result = service.install_agent_adapter(adapter, workdir=workdir)

    assert result["status"] == "installed"
    for relative_path in old_paths:
        assert relative_path in result["removed_obsolete_files"]
        assert not (workdir / relative_path).exists()
    manifest = json.loads((workdir / ".loopora" / "adapters" / adapter / "manifest.json").read_text(encoding="utf-8"))
    managed_paths = {item["path"] for item in manifest["managed_files"]}
    assert all(relative_path not in managed_paths for relative_path in old_paths)
