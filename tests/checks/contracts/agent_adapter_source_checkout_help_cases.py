from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from loopora import agent_adapter_command_prefix, cli


def assert_project_file_cli_entry_anchors_source_checkout_uv_commands(monkeypatch) -> None:
    source_root = agent_adapter_command_prefix.loopora_source_checkout_root()
    assert source_root is not None
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")

    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    assert (
        agent_adapter_command_prefix.current_project_file_loopora_cli_entry()
        == f"uv --directory {shlex.quote(str(source_root))} run loopora"
    )

    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run python -m loopora")
    assert (
        agent_adapter_command_prefix.current_project_file_loopora_cli_entry()
        == f"uv --directory {shlex.quote(str(source_root))} run python -m loopora"
    )

    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "loopora")
    assert agent_adapter_command_prefix.current_project_file_loopora_cli_entry() == "loopora"


def assert_source_checkout_help_command_rewrite_is_idempotent(monkeypatch) -> None:
    source_root = agent_adapter_command_prefix.loopora_source_checkout_root()
    assert source_root is not None
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    source_entry = f"uv --directory {shlex.quote(str(source_root))} run loopora"
    raw_help = (
        'Use `loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742`, '
        "`loopora doctor --workdir \"$PWD\"`, and `loopora loops`."
    )

    rewritten_once = agent_adapter_command_prefix.rewrite_loopora_help_commands(raw_help)
    rewritten_twice = agent_adapter_command_prefix.rewrite_loopora_help_commands(rewritten_once)

    assert rewritten_once == rewritten_twice
    assert f"`{source_entry} serve --open --workdir \"$PWD\" --host 127.0.0.1 --port 8742`" in rewritten_once
    assert f"`{source_entry} doctor --workdir \"$PWD\"`" in rewritten_once
    assert f"`{source_entry} loops`" in rewritten_once


def assert_source_checkout_help_epilogs_preserve_project_file_cli_entry() -> None:
    source_root = agent_adapter_command_prefix.loopora_source_checkout_root()
    assert source_root is not None
    source_entry = f"uv --directory {shlex.quote(str(source_root))} run loopora"
    help_cases = [
        (
            ("loops",),
            (
                f"`{source_entry} fit`",
                    f"`{source_entry} serve --open --workdir \"$PWD\" --host 127.0.0.1 --port 8742`",
                f"`{source_entry} init <agent> --workdir \"$PWD\"`",
                f"`{source_entry} doctor --workdir \"$PWD\"`",
            ),
        ),
        (("loops", "create"), (f"`{source_entry} loops create`",)),
        (
            ("init", "codex"),
            (
                f"`{source_entry} fit`",
                f"`{source_entry} init codex --workdir \"$PWD\"`",
                f"`{source_entry} doctor --workdir \"$PWD\"`",
                    f"`{source_entry} serve --open --workdir \"$PWD\" --host 127.0.0.1 --port 8742`",
                f"`{source_entry} loops`",
            ),
        ),
        (("uninstall", "codex"), (f"`{source_entry} init codex --workdir \"$PWD\"`",)),
        (("agent", "codex"), (f"`{source_entry} init codex --workdir \"$PWD\"`",)),
        (("agent", "codex", "check"), (f"`{source_entry} doctor --workdir \"$PWD\"`", f"`{source_entry} init codex --workdir ...`")),
        (("dev",), (f"`{source_entry} dev check --list`", f"`{source_entry} dev reset`")),
        (("dev", "reset"), (f"`{source_entry} doctor --workdir <project>`",)),
        (("spec",), (f"`{source_entry} fit`",)),
        (("spec", "init"), (f"`{source_entry} start`", f"`{source_entry} fit`")),
        (("spec", "template"), (f"`{source_entry} start`", f"`{source_entry} fit`")),
        (("spec", "write"), (f"`{source_entry} spec validate`",)),
            (("bundles", "import"), (f"`{source_entry} start`", f"`{source_entry} serve --open --workdir \"$PWD\" --host 127.0.0.1 --port 8742`")),
        (("prompts",), (f"`{source_entry} fit`", f"`{source_entry} spec`")),
    ]
    env = {**os.environ, "COLUMNS": "300"}

    for args, expected_fragments in help_cases:
        result = subprocess.run(
            ["uv", "run", "loopora", *args, "--help"],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        output = result.stdout + result.stderr
        normalized_output = " ".join(output.split())
        assert result.returncode == 0, output
        assert all(fragment in normalized_output for fragment in expected_fragments)


def monkeypatch_source_checkout_cli_entry(monkeypatch) -> str:
    monkeypatch.setattr(agent_adapter_command_prefix, "current_loopora_cli_entry", lambda: "uv run loopora")
    monkeypatch.setenv("UV_RUN_RECURSION_DEPTH", "1")
    source_root = agent_adapter_command_prefix.loopora_source_checkout_root()
    assert source_root is not None
    return f"uv --directory {shlex.quote(str(source_root))} run loopora"


def assert_cli_adapter_install_managed_entries_preserve_current_cli_entry(
    monkeypatch,
    tmp_path: Path,
    *,
    adapter: str,
    entry_source: str,
    entry_root: str,
) -> None:
    workdir = tmp_path / f"{adapter} source checkout"
    workdir.mkdir()
    runner = CliRunner()
    source_entry = monkeypatch_source_checkout_cli_entry(monkeypatch)

    result = runner.invoke(cli.app, ["init", adapter, "--workdir", str(workdir), "--json"])

    assert result.exit_code == 0, result.stdout
    plan_entry_path, run_entry_path, plan_contract_path, run_contract_path = _managed_entry_paths(
        workdir,
        adapter=adapter,
        entry_root=entry_root,
    )
    plan_entry = plan_entry_path.read_text(encoding="utf-8")
    run_entry = run_entry_path.read_text(encoding="utf-8")
    plan_contract = plan_contract_path.read_text(encoding="utf-8")
    run_contract = run_contract_path.read_text(encoding="utf-8")
    _assert_managed_entry_commands_preserve_project_entry(
        adapter=adapter,
        entry_source=entry_source,
        source_entry=source_entry,
        texts=(plan_entry, run_entry, plan_contract, run_contract),
    )
    if adapter == "claude":
        session_context = (
            workdir / ".claude" / "hooks" / "loopora-session-context.additional-context.md"
        ).read_text(encoding="utf-8")
        hook_script = (workdir / ".claude" / "hooks" / "loopora-session-context.py").read_text(encoding="utf-8")
        _assert_claude_project_file_entry(
            source_entry=source_entry,
            plan_entry=plan_entry,
            run_entry=run_entry,
            session_context=session_context,
            hook_script=hook_script,
        )


def _managed_entry_paths(
    workdir: Path,
    *,
    adapter: str,
    entry_root: str,
) -> tuple[Path, Path, Path, Path]:
    if adapter == "opencode":
        return (
            workdir / entry_root / "commands" / "loopora-plan.md",
            workdir / entry_root / "commands" / "loopora-run.md",
            workdir / entry_root / "loopora" / "references" / "loopora-plan-contract.md",
            workdir / entry_root / "loopora" / "references" / "loopora-run-contract.md",
        )
    return (
        workdir / entry_root / "loopora-plan" / "SKILL.md",
        workdir / entry_root / "loopora-run" / "SKILL.md",
        workdir / entry_root / "loopora-plan" / "references" / "loopora-plan-contract.md",
        workdir / entry_root / "loopora-run" / "references" / "loopora-run-contract.md",
    )


def _assert_managed_entry_commands_preserve_project_entry(
    *,
    adapter: str,
    entry_source: str,
    source_entry: str,
    texts: tuple[str, str, str, str],
) -> None:
    plan_entry, run_entry, plan_contract, run_contract = texts
    plan_command = f"LOOPORA_AGENT_ENTRY_SOURCE={entry_source} {source_entry} agent {adapter} plan --workdir \"$PWD\""
    run_command = f"LOOPORA_AGENT_ENTRY_SOURCE={entry_source} {source_entry} agent {adapter} run --workdir \"$PWD\""
    unanchored_plan_command = f"LOOPORA_AGENT_ENTRY_SOURCE={entry_source} uv run loopora agent {adapter} plan --workdir \"$PWD\""
    unanchored_run_command = f"LOOPORA_AGENT_ENTRY_SOURCE={entry_source} uv run loopora agent {adapter} run --workdir \"$PWD\""
    bare_plan_command = f"LOOPORA_AGENT_ENTRY_SOURCE={entry_source} loopora agent {adapter} plan --workdir \"$PWD\""
    bare_run_command = f"LOOPORA_AGENT_ENTRY_SOURCE={entry_source} loopora agent {adapter} run --workdir \"$PWD\""

    assert plan_command in plan_entry
    assert plan_command in plan_contract
    assert run_command in run_entry
    assert run_command in run_contract
    assert unanchored_plan_command not in plan_entry
    assert unanchored_plan_command not in plan_contract
    assert unanchored_run_command not in run_entry
    assert unanchored_run_command not in run_contract
    assert bare_plan_command not in plan_entry
    assert bare_plan_command not in plan_contract
    assert bare_run_command not in run_entry
    assert bare_run_command not in run_contract
    assert f"`{source_entry} agent {adapter} plan`" in plan_contract
    assert f"`{source_entry} agent {adapter} run`" in run_contract
    assert f"`{source_entry} init {adapter} --check --workdir \"$PWD\"`" in run_contract
    assert f"`{source_entry} agent {adapter} check --workdir \"$PWD\"`" in run_contract
    assert f"`{source_entry} init {adapter} --workdir \"$PWD\"`" in run_contract


def _assert_claude_project_file_entry(
    *,
    source_entry: str,
    plan_entry: str,
    run_entry: str,
    session_context: str,
    hook_script: str,
) -> None:
    assert f"Bash({source_entry} agent claude plan *)" in plan_entry
    assert f"Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {source_entry} agent claude plan *)" in plan_entry
    assert "Bash(uv run loopora agent claude plan *)" not in plan_entry
    assert "Bash(loopora agent claude plan *)" not in plan_entry
    assert f"Bash({source_entry} agent claude run *)" in run_entry
    assert f"Bash({source_entry} init claude *)" in run_entry
    assert f"LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill {source_entry} agent claude plan" in session_context
    assert "LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill uv run loopora agent claude plan" not in session_context
    assert "LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan" not in session_context
    assert "REPAIR_COMMAND =" in hook_script
    assert f"{source_entry} init claude --check --workdir" in hook_script
    assert "$CLAUDE_PROJECT_DIR" in hook_script
