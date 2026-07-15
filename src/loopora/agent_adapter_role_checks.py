from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

from loopora.agent_adapter_manifest import adapter_check, markdown_frontmatter, read_text_or_empty
from loopora.system_prompt_assets import load_system_prompt_asset

CODEX_ROLE_CONTRACT_SNIPPETS_ASSET = "agent_native/codex-role-contract-check-snippets.md"
CODEX_ORCHESTRATOR_CONTRACT_SNIPPETS_ASSET = "agent_native/codex-orchestrator-contract-check-snippets.md"
CLAUDE_ROLE_TOOL_ALLOWLISTS = {
    "orchestrator": {"Agent", "Task", "Read", "Write", "Bash"},
    "builder": {"Read", "Glob", "Grep", "Bash", "Write", "Edit", "MultiEdit"},
    "inspector": {"Read", "Glob", "Grep", "Bash"},
    "gatekeeper": {"Read", "Glob", "Grep", "Bash"},
    "guide": {"Read", "Glob", "Grep", "Bash"},
}
CLAUDE_ROLE_MAX_TURNS = {
    "orchestrator": 20,
    "builder": 20,
    "inspector": 12,
    "gatekeeper": 12,
    "guide": 12,
}
OPENCODE_DISPATCH_ROLE_AGENTS = ("loopora-builder", "loopora-inspector", "loopora-gatekeeper", "loopora-guide")


def codex_role_agent_checks(
    root: Path,
    role_agent_paths: dict[str, str],
    *,
    install_command: str,
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for role, relative_path in role_agent_paths.items():
        target = root / relative_path
        if not target.exists():
            continue
        payload, error = _read_toml_or_error(target)
        gaps = _codex_role_agent_gaps(role, payload)
        if error:
            gaps.append("valid TOML")
        checks.append(
            adapter_check(
                "role_permissions",
                ok=not gaps,
                path=relative_path,
                message="" if not gaps else _codex_role_agent_message(role, gaps, install_command, error=error),
            )
        )
    return checks


def claude_role_agent_checks(
    root: Path,
    role_agent_paths: dict[str, str],
    *,
    install_command: str,
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for role, relative_path in role_agent_paths.items():
        target = root / relative_path
        if not target.exists():
            continue
        metadata = markdown_frontmatter(read_text_or_empty(target))
        gaps = _claude_role_agent_gaps(role, metadata)
        checks.append(
            adapter_check(
                "role_permissions",
                ok=not gaps,
                path=relative_path,
                message="" if not gaps else _claude_role_agent_message(role, gaps, install_command),
            )
        )
    return checks


def opencode_role_permission_checks(
    root: Path,
    role_agent_paths: dict[str, str],
    *,
    install_command: str,
) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for role, relative_path in role_agent_paths.items():
        target = root / relative_path
        if not target.exists():
            continue
        metadata = markdown_frontmatter(read_text_or_empty(target))
        gaps = _opencode_role_permission_gaps(role, metadata)
        checks.append(
            adapter_check(
                "role_permissions",
                ok=not gaps,
                path=relative_path,
                message="" if not gaps else _opencode_role_permission_message(role, gaps, install_command),
            )
        )
    return checks


def _codex_role_agent_gaps(role: str, payload: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if payload.get("name") != f"loopora-{role}":
        gaps.append(f"name=loopora-{role}")
    if not str(payload.get("description") or "").strip():
        gaps.append("description")
    developer_instructions = str(payload.get("developer_instructions") or "")
    if not developer_instructions.strip():
        gaps.append("developer_instructions")
        return gaps
    expected_snippets = _codex_contract_check_snippets(role)
    gaps.extend(
        f"developer_instructions contains {snippet}"
        for snippet in expected_snippets
        if snippet not in developer_instructions
    )
    return gaps


def _codex_contract_check_snippets(role: str) -> tuple[str, ...]:
    asset_ref = CODEX_ORCHESTRATOR_CONTRACT_SNIPPETS_ASSET if role == "orchestrator" else CODEX_ROLE_CONTRACT_SNIPPETS_ASSET
    return tuple(line.strip() for line in load_system_prompt_asset(asset_ref).splitlines() if line.strip())


def _read_toml_or_error(path: Path) -> tuple[dict[str, Any], str]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return {}, str(exc)
    return (payload if isinstance(payload, dict) else {}), ""


def _codex_role_agent_message(role: str, gaps: list[str], install_command: str, *, error: str = "") -> str:
    drift = ", ".join(gaps)
    details = f"; parse error: {error}" if error else ""
    return (
        f"Codex loopora-{role} must preserve discoverable TOML metadata and the Loopora role contract; "
        f"drift: {drift}{details}; run {install_command} to restore managed role agent config"
    )


def _claude_role_agent_gaps(role: str, metadata: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if metadata.get("name") != f"loopora-{role}":
        gaps.append(f"name=loopora-{role}")
    if not str(metadata.get("description") or "").strip():
        gaps.append("description")
    if metadata.get("maxTurns") != CLAUDE_ROLE_MAX_TURNS.get(role):
        gaps.append(f"maxTurns={CLAUDE_ROLE_MAX_TURNS.get(role)}")
    expected_tools = CLAUDE_ROLE_TOOL_ALLOWLISTS.get(role, set())
    actual_tools = _claude_tools(metadata.get("tools"))
    if actual_tools != expected_tools:
        gaps.append("tools=" + ",".join(sorted(expected_tools)))
    return gaps


def _claude_tools(value: object) -> set[str]:
    if isinstance(value, list):
        return {str(item).strip() for item in value if str(item).strip()}
    return {item.strip() for item in str(value or "").split(",") if item.strip()}


def _claude_role_agent_message(role: str, gaps: list[str], install_command: str) -> str:
    drift = ", ".join(gaps)
    return (
        f"Claude Code loopora-{role} must preserve discoverable frontmatter and role tool allowlist; "
        f"drift: {drift}; run {install_command} to restore managed role agent config"
    )


def _opencode_role_permission_gaps(role: str, metadata: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if metadata.get("mode") != "subagent":
        gaps.append("mode=subagent")
    permission = metadata.get("permission")
    task_permission = permission.get("task") if isinstance(permission, dict) else None
    if role == "orchestrator":
        if not isinstance(task_permission, dict):
            return [*gaps, "permission.task allowlist"]
        expected_targets = set(OPENCODE_DISPATCH_ROLE_AGENTS)
        if task_permission.get("*") != "deny":
            gaps.append('permission.task."*"=deny')
        gaps.extend(
            f"permission.task.{target_agent}=allow"
            for target_agent in OPENCODE_DISPATCH_ROLE_AGENTS
            if task_permission.get(target_agent) != "allow"
        )
        for target_agent, value in sorted(task_permission.items()):
            if target_agent not in expected_targets | {"*"} and value != "deny":
                gaps.append(f"permission.task.{target_agent}=deny")
        return gaps
    if task_permission != "deny":
        gaps.append("permission.task=deny")
    return gaps


def _opencode_role_permission_message(role: str, gaps: list[str], install_command: str) -> str:
    drift = ", ".join(gaps)
    if role == "orchestrator":
        return (
            "OpenCode loopora-orchestrator must deny wildcard task calls and allow only Loopora role agents; "
            f"drift: {drift}; run {install_command} to restore managed role permissions"
        )
    return (
        f"OpenCode loopora-{role} must keep permission.task deny so role work cannot spawn nested subagents/provider flows; "
        f"drift: {drift}; run {install_command} to restore managed role permissions"
    )
