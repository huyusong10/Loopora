from __future__ import annotations

from agent_adapter_test_support import LooporaConflictError, Path, json, pytest


def test_adapter_project_entries_are_namespaced_and_do_not_set_host_models(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    banned_model_defaults = (
        "gpt-",
        "anthropic/",
        "openai/",
        "model =",
        "\nmodel:",
        "reasoning_effort =",
        "\nreasoning_effort:",
    )

    for adapter in ("codex", "claude", "opencode"):
        workdir = tmp_path / adapter
        workdir.mkdir()
        service.install_agent_adapter(adapter, workdir=workdir)
        manifest = json.loads((workdir / ".loopora" / "adapters" / adapter / "manifest.json").read_text(encoding="utf-8"))
        managed_paths = [item["path"] for item in manifest["managed_files"]]
        assert managed_paths
        for relative_path in managed_paths:
            name = Path(relative_path).name
            if relative_path.endswith((".md", ".toml")) and "loopora-session-context" not in relative_path:
                assert name.startswith("loopora-") or name == "SKILL.md"
            text = (workdir / relative_path).read_text(encoding="utf-8")
            for banned in banned_model_defaults:
                assert banned not in text
        assert not (workdir / ".claude" / "commands" / "loopora-plan.md").exists()


def test_codex_adapter_install_does_not_touch_user_configuration(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()
    agents = workdir / "AGENTS.md"
    codex_config = workdir / ".codex" / "config.toml"
    codex_config.parent.mkdir()
    agents.write_text("# User project rules\n", encoding="utf-8")
    codex_config.write_text("model = \"user-choice\"\n", encoding="utf-8")

    service.install_agent_adapter("codex", workdir=workdir)
    service.uninstall_agent_adapter("codex", workdir=workdir)

    assert agents.read_text(encoding="utf-8") == "# User project rules\n"
    assert codex_config.read_text(encoding="utf-8") == "model = \"user-choice\"\n"


def test_codex_adapter_refuses_unowned_target_files(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    custom_skill = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    custom_skill.parent.mkdir(parents=True)
    custom_skill.write_text("# User-owned skill\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError):
        service.install_agent_adapter("codex", workdir=workdir)

    assert custom_skill.read_text(encoding="utf-8") == "# User-owned skill\n"


def test_claude_adapter_refuses_unowned_target_files(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    custom_skill = workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md"
    custom_skill.parent.mkdir(parents=True)
    custom_skill.write_text("# User-owned Claude skill\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError):
        service.install_agent_adapter("claude", workdir=workdir)

    assert custom_skill.read_text(encoding="utf-8") == "# User-owned Claude skill\n"


def test_opencode_adapter_refuses_unowned_target_files(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    custom_command = workdir / ".opencode" / "commands" / "loopora-plan.md"
    custom_command.parent.mkdir(parents=True)
    custom_command.write_text("# User-owned OpenCode command\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError):
        service.install_agent_adapter("opencode", workdir=workdir)

    assert custom_command.read_text(encoding="utf-8") == "# User-owned OpenCode command\n"
