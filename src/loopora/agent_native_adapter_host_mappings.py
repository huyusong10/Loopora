from __future__ import annotations

ROLE_AGENT_KINDS = ("builder", "inspector", "gatekeeper", "guide", "orchestrator")


def agent_adapter_entry_kind(kind: str) -> str:
    if kind == "opencode":
        return "project_command"
    return "project_skill"


def agent_adapter_entry_paths(kind: str) -> dict[str, str]:
    if kind == "codex":
        return {
            "plan": ".agents/skills/loopora-plan/SKILL.md",
            "run": ".agents/skills/loopora-run/SKILL.md",
        }
    if kind == "claude":
        return {
            "plan": ".claude/skills/loopora-plan/SKILL.md",
            "run": ".claude/skills/loopora-run/SKILL.md",
        }
    if kind == "opencode":
        return {
            "plan": ".opencode/commands/loopora-plan.md",
            "run": ".opencode/commands/loopora-run.md",
        }
    return {}


def agent_adapter_role_agent_paths(kind: str) -> dict[str, str]:
    if kind == "codex":
        return {role: f".codex/agents/loopora-{role}.toml" for role in ROLE_AGENT_KINDS}
    if kind == "claude":
        return {role: f".claude/agents/loopora-{role}.md" for role in ROLE_AGENT_KINDS}
    if kind == "opencode":
        return {role: f".opencode/agents/loopora-{role}.md" for role in ROLE_AGENT_KINDS}
    return {}


def agent_adapter_role_agent_map(kind: str) -> dict[str, dict[str, str]]:
    return {
        role: {
            "target_agent": f"loopora-{role}",
            "path": path,
        }
        for role, path in agent_adapter_role_agent_paths(kind).items()
    }


def agent_adapter_context_identity_env(kind: str) -> list[str]:
    if kind == "codex":
        return ["LOOPORA_AGENT_SESSION_ID", "CODEX_SESSION_ID", "CODEX_THREAD_ID"]
    if kind == "claude":
        return ["LOOPORA_AGENT_SESSION_ID", "CLAUDE_SESSION_ID"]
    if kind == "opencode":
        return ["LOOPORA_AGENT_SESSION_ID", "OPENCODE_SESSION_ID"]
    return ["LOOPORA_AGENT_SESSION_ID"]
