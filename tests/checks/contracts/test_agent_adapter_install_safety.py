from __future__ import annotations

from agent_adapter_test_support import LooporaConflictError, Path, json, pytest
from loopora import agent_adapter_host_config, agent_adapter_managed_files
from loopora.service_types import LooporaWorkdirUnavailableError


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


def test_agent_adapter_service_requires_explicit_usable_workdir_without_cwd(
    monkeypatch,
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    monkeypatch.chdir(tmp_path)
    missing_workdir = tmp_path / "missing-project"
    calls = [
        ("list_agent_adapters", (), {}, "required"),
        ("get_agent_adapter", ("codex",), {}, "required"),
        ("check_agent_adapter", ("codex",), {}, "required"),
        ("install_agent_adapter", ("codex",), {}, "required"),
        ("preview_agent_adapter_uninstall", ("codex",), {}, "required"),
        ("uninstall_agent_adapter", ("codex",), {}, "required"),
        ("install_agent_adapter", ("codex",), {"workdir": missing_workdir}, "missing"),
    ]

    for method_name, args, kwargs, expected_state in calls:
        with pytest.raises(LooporaWorkdirUnavailableError) as exc_info:
            getattr(service, method_name)(*args, **kwargs)
        assert exc_info.value.action == "agent"
        assert exc_info.value.workdir_state == expected_state
        assert str(exc_info.value) == f"target project is not ready for same-Agent project entries: {exc_info.value.summary}"

    assert not (tmp_path / ".loopora" / "adapters").exists()
    assert not missing_workdir.exists()


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


def test_agent_adapter_uninstall_preview_uses_delete_guard_without_removing_files(service_factory, tmp_path: Path) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()

    service.install_agent_adapter("codex", workdir=workdir)
    managed_skill = workdir / ".agents" / "skills" / "loopora-plan" / "SKILL.md"
    preview = service.preview_agent_adapter_uninstall("codex", workdir=workdir)

    assert preview["status"] == "dry_run"
    assert preview["dry_run"] is True
    assert preview["would_delete"]["removed_file_count"] == len(preview["removed_files"])
    assert ".agents/skills/loopora-plan/SKILL.md" in preview["removed_files"]
    assert preview["kept_files"] == []
    assert managed_skill.exists()


def test_agent_adapter_uninstall_checks_host_config_before_deleting_managed_files(
    service_factory,
    tmp_path: Path,
) -> None:
    service = service_factory(scenario="success")
    workdir = tmp_path / "project"
    workdir.mkdir()
    service.install_agent_adapter("claude", workdir=workdir)
    managed_skill = workdir / ".claude" / "skills" / "loopora-plan" / "SKILL.md"
    claude_settings = workdir / ".claude" / "settings.json"
    claude_settings.write_text("{not json\n", encoding="utf-8")

    with pytest.raises(LooporaConflictError):
        service.uninstall_agent_adapter("claude", workdir=workdir)

    assert managed_skill.exists()
    assert claude_settings.read_text(encoding="utf-8") == "{not json\n"


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


def test_agent_adapter_managed_file_atomic_write_cleans_temp_on_replace_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "project" / ".codex" / "agents" / "loopora-builder.toml"
    original_replace = Path.replace

    def fail_replace(path: Path, target_path: Path) -> Path:
        if Path(target_path) == target:
            raise PermissionError(f"permission denied: {target_path}")
        return original_replace(path, target_path)

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(PermissionError):
        agent_adapter_managed_files.atomic_write_text(target, "managed content\n")

    assert list(target.parent.glob(f".{target.name}.tmp.*")) == []


def test_claude_host_config_atomic_write_cleans_temp_on_replace_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "project"
    settings_path = root / ".claude" / "settings.json"
    original_replace = Path.replace

    def fail_settings_replace(path: Path, target_path: Path) -> Path:
        if Path(target_path) == settings_path:
            raise PermissionError(f"permission denied: {target_path}")
        return original_replace(path, target_path)

    monkeypatch.setattr(Path, "replace", fail_settings_replace)

    with pytest.raises(PermissionError):
        agent_adapter_host_config.install_host_config("claude", root)

    assert list(settings_path.parent.glob(f"{settings_path.name}.tmp")) == []
