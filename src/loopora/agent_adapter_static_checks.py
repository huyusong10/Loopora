from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from loopora.agent_adapter_check_utils import (
    adapter_check,
    adapter_label,
    read_text_or_empty,
)
from loopora.agent_adapter_command_prefix import prefix_loopora_command
from loopora.agent_adapter_entry_static_checks import (
    adapter_entry_shape_checks,
    adapter_reference_paths,
    adapter_supporting_files_checks,
)
from loopora.agent_adapter_host_config import (
    CLAUDE_SESSION_HOOK_RELATIVE_PATH,
    claude_session_hook_check_passes,
)
from loopora.agent_adapter_manifest import manifest_relative_path
from loopora.agent_adapter_role_checks import (
    claude_role_agent_checks,
    codex_role_agent_checks,
    opencode_role_permission_checks,
)
from loopora.agent_adapter_templates import managed_templates
from loopora.agent_native_adapter_contracts import (
    agent_adapter_native_surface_summary,
    agent_adapter_role_agent_paths,
)


def adapter_static_checks(kind: str, root: Path, status: dict[str, Any]) -> list[dict[str, str]]:
    checks = [
        adapter_check(
            "managed_manifest",
            ok=status.get("status") == "installed",
            path=str(status.get("manifest_path") or ""),
            message=str(status.get("summary") or ""),
        )
    ]
    checks.append(adapter_no_model_defaults_check(kind, root))
    checks.extend(adapter_supporting_files_checks(kind, root))
    checks.extend(adapter_entry_shape_checks(kind, root))
    checks.extend(adapter_role_agent_checks(kind, root))
    if kind == "claude":
        checks.append(
            adapter_check(
                "claude_session_hook",
                ok=claude_session_hook_check_passes(root),
                path=CLAUDE_SESSION_HOOK_RELATIVE_PATH,
            )
        )
    if kind == "opencode":
        checks.append(
            adapter_check(
                "opencode_orchestrator_command",
                ok=opencode_run_command_check_passes(root),
                path=".opencode/commands/loopora-run.md",
            )
        )
    return checks


def adapter_install_next_steps(kind: str) -> list[str]:
    label = adapter_label(kind)
    return [
        f"Return to {label} in this project with the task goal, fake-done risk, and required evidence.",
        "Run /loopora-plan to prepare the Loop preview before starting work.",
        "Review the READY Loop preview, then run /loopora-run in the same Agent session.",
        adapter_entry_visibility_hint(kind),
        "Use Web to observe evidence, gaps, and verdicts while execution stays in the Agent.",
    ]


def adapter_entry_visibility_hint(kind: str) -> str:
    label = adapter_label(kind)
    if kind == "opencode":
        entry_paths = ".opencode/commands/loopora-plan.md and .opencode/commands/loopora-run.md"
    elif kind == "claude":
        entry_paths = ".claude/skills/loopora-plan/SKILL.md and .claude/skills/loopora-run/SKILL.md"
    else:
        entry_paths = ".agents/skills/loopora-plan/SKILL.md and .agents/skills/loopora-run/SKILL.md"
    return (
        f"If /loopora-plan or /loopora-run is not visible in {label}, verify the managed entry files at "
        f"{entry_paths}, then refresh or restart {label}."
    )


def adapter_install_next_commands(kind: str, root: Path) -> dict[str, str]:
    workdir_arg = shlex.quote(str(root))
    return {
        "plan": "/loopora-plan",
        "run": "/loopora-run",
        "check": prefix_loopora_command(f"loopora init {kind} --workdir {workdir_arg} --check"),
        "agent_check": prefix_loopora_command(f"loopora agent {kind} check --workdir {workdir_arg}"),
    }


def adapter_native_surface(kind: str, root: Path) -> dict[str, Any]:
    next_commands = adapter_install_next_commands(kind, root)
    surface = agent_adapter_native_surface_summary(kind)
    return {
        **surface,
        "reference_paths": adapter_reference_paths(kind),
        "owned_state": [
            ".loopora/",
            manifest_relative_path(kind),
        ],
        "diagnostics": {
            "check_command": next_commands["check"],
            "agent_check_command": next_commands["agent_check"],
        },
    }


def adapter_no_model_defaults_check(kind: str, root: Path) -> dict[str, str]:
    banned = ("gpt-", "anthropic/", "openai/", "model =", "\nmodel:", "reasoning_effort =", "\nreasoning_effort:", "provider:")
    offenders: list[str] = []
    for relative_path in managed_templates(kind):
        if not relative_path.endswith((".md", ".toml")) or "loopora-session-context" in relative_path:
            continue
        target = root / relative_path
        if not target.exists():
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            offenders.append(relative_path)
            continue
        if any(item in text for item in banned):
            offenders.append(relative_path)
    return adapter_check(
        "no_host_model_defaults",
        ok=not offenders,
        message=", ".join(offenders),
    )


def adapter_role_agent_checks(kind: str, root: Path) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for relative_path in agent_adapter_role_agent_paths(kind).values():
        exists = (root / relative_path).exists()
        checks.append(
            adapter_check(
                "role_agent",
                ok=exists,
                path=relative_path,
                message="" if exists else adapter_missing_role_agent_message(kind, root, relative_path),
            )
        )
    if kind == "codex":
        install_command = prefix_loopora_command(f"loopora init codex --workdir {shlex.quote(str(root))}")
        checks.extend(
            codex_role_agent_checks(
                root,
                agent_adapter_role_agent_paths("codex"),
                install_command=install_command,
            )
        )
    if kind == "claude":
        install_command = prefix_loopora_command(f"loopora init claude --workdir {shlex.quote(str(root))}")
        checks.extend(
            claude_role_agent_checks(
                root,
                agent_adapter_role_agent_paths("claude"),
                install_command=install_command,
            )
        )
    if kind == "opencode":
        install_command = prefix_loopora_command(f"loopora init opencode --workdir {shlex.quote(str(root))}")
        checks.extend(
            opencode_role_permission_checks(
                root,
                agent_adapter_role_agent_paths("opencode"),
                install_command=install_command,
            )
        )
    return checks


def adapter_missing_role_agent_message(kind: str, root: Path, relative_path: str) -> str:
    target_agent = Path(relative_path).stem
    install_command = prefix_loopora_command(f"loopora init {kind} --workdir {shlex.quote(str(root))}")
    return f"managed role agent config for {target_agent} is missing; run {install_command} before /loopora-run dispatch"


def opencode_run_command_check_passes(root: Path) -> bool:
    text = read_text_or_empty(root / ".opencode/commands/loopora-run.md")
    return "agent: loopora-orchestrator" in text and "subtask: true" in text
