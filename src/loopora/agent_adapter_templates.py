from __future__ import annotations

from loopora.agent_adapter_entry_contracts import (
    agent_plan_contract as _agent_plan_contract,
    agent_recovery_matrix as _agent_recovery_matrix,
    agent_result_template_guide as _agent_result_template_guide,
    agent_role_dispatch_guide as _agent_role_dispatch_guide,
)
from loopora.agent_adapter_entry_templates import (
    claude_loopora_gen_skill as _entry_claude_loopora_gen_skill,
    claude_loopora_loop_skill as _entry_claude_loopora_loop_skill,
    codex_loopora_gen_skill as _entry_codex_loopora_gen_skill,
    codex_loopora_loop_skill as _entry_codex_loopora_loop_skill,
    opencode_loopora_gen_command as _entry_opencode_loopora_gen_command,
    opencode_loopora_loop_command as _entry_opencode_loopora_loop_command,
)
from loopora.agent_adapter_run_contract import agent_native_loop_body as _entry_agent_native_loop_body
from loopora.agent_adapter_host_config import (
    CLAUDE_SESSION_HOOK_RELATIVE_PATH,
    claude_session_hook_script as _claude_session_hook_script,
)
from loopora.agent_adapter_role_contracts import (
    role_agent_body,
    role_agent_description,
)
from loopora.service_types import LooporaError

ADAPTER_MANAGED_SCHEMA_VERSION = 3
ADAPTER_VERSION = 30
CODEX_ADAPTER_VERSION = ADAPTER_VERSION
CLAUDE_ADAPTER_VERSION = ADAPTER_VERSION
OPENCODE_ADAPTER_VERSION = ADAPTER_VERSION
CODEX_MANAGED_MARKER = "LOOPORA-MANAGED: codex-adapter"
CLAUDE_MANAGED_MARKER = "LOOPORA-MANAGED: claude-code-adapter"
OPENCODE_MANAGED_MARKER = "LOOPORA-MANAGED: opencode-adapter"
MANAGED_MARKERS = {
    "codex": CODEX_MANAGED_MARKER,
    "claude": CLAUDE_MANAGED_MARKER,
    "opencode": OPENCODE_MANAGED_MARKER,
}
MANAGED_MARKER = CODEX_MANAGED_MARKER


def _adapter_label(kind: str) -> str:
    return {
        "codex": "Codex",
        "claude": "Claude Code",
        "opencode": "OpenCode",
    }.get(kind, kind)


def managed_templates(kind: str) -> dict[str, str]:
    if kind == "codex":
        return _codex_managed_templates()
    if kind == "claude":
        return _claude_managed_templates()
    if kind == "opencode":
        return _opencode_managed_templates()
    raise LooporaError(f"{_adapter_label(kind)} adapter is not implemented yet")


def _codex_managed_templates() -> dict[str, str]:
    return {
        ".agents/skills/loopora-plan/SKILL.md": _codex_loopora_gen_skill(),
        ".agents/skills/loopora-plan/references/loopora-plan-contract.md": _agent_plan_contract("codex", "Codex", "codex_project_skill"),
        ".agents/skills/loopora-run/SKILL.md": _codex_loopora_loop_skill(),
        ".agents/skills/loopora-run/references/loopora-run-contract.md": _agent_native_loop_body(adapter="codex", marker_source="codex_project_skill"),
        ".agents/skills/loopora-run/references/loopora-recovery-matrix.md": _agent_recovery_matrix(),
        ".agents/skills/loopora-run/references/loopora-result-template-guide.md": _agent_result_template_guide("codex"),
        ".agents/skills/loopora-run/references/loopora-role-dispatch-guide.md": _agent_role_dispatch_guide("codex"),
        ".codex/agents/loopora-builder.toml": _codex_role_agent("builder"),
        ".codex/agents/loopora-inspector.toml": _codex_role_agent("inspector"),
        ".codex/agents/loopora-gatekeeper.toml": _codex_role_agent("gatekeeper"),
        ".codex/agents/loopora-guide.toml": _codex_role_agent("guide"),
        ".codex/agents/loopora-orchestrator.toml": _codex_role_agent("orchestrator"),
    }


def _claude_managed_templates() -> dict[str, str]:
    return {
        ".claude/skills/loopora-plan/SKILL.md": _claude_loopora_gen_skill(),
        ".claude/skills/loopora-plan/references/loopora-plan-contract.md": _agent_plan_contract("claude", "Claude Code", "claude_project_skill", context_arg='--context-id "${CLAUDE_SESSION_ID}"'),
        ".claude/skills/loopora-run/SKILL.md": _claude_loopora_loop_skill(),
        ".claude/skills/loopora-run/references/loopora-run-contract.md": _agent_native_loop_body(adapter="claude", marker_source="claude_project_skill", context_arg='--context-id "${CLAUDE_SESSION_ID}"'),
        ".claude/skills/loopora-run/references/loopora-recovery-matrix.md": _agent_recovery_matrix(),
        ".claude/skills/loopora-run/references/loopora-result-template-guide.md": _agent_result_template_guide("claude"),
        ".claude/skills/loopora-run/references/loopora-role-dispatch-guide.md": _agent_role_dispatch_guide("claude"),
        CLAUDE_SESSION_HOOK_RELATIVE_PATH: _claude_session_hook_script(
            marker=CLAUDE_MANAGED_MARKER,
            version=CLAUDE_ADAPTER_VERSION,
        ),
        ".claude/agents/loopora-builder.md": _claude_role_agent("builder"),
        ".claude/agents/loopora-inspector.md": _claude_role_agent("inspector"),
        ".claude/agents/loopora-gatekeeper.md": _claude_role_agent("gatekeeper"),
        ".claude/agents/loopora-guide.md": _claude_role_agent("guide"),
        ".claude/agents/loopora-orchestrator.md": _claude_role_agent("orchestrator"),
    }


def _opencode_managed_templates() -> dict[str, str]:
    return {
        ".opencode/commands/loopora-plan.md": _opencode_loopora_gen_command(),
        ".opencode/loopora/references/loopora-plan-contract.md": _agent_plan_contract("opencode", "OpenCode", "opencode_project_command", context_arg='--context-id "${OPENCODE_SESSION_ID:-}"', supports_arguments=True),
        ".opencode/commands/loopora-run.md": _opencode_loopora_loop_command(),
        ".opencode/loopora/references/loopora-run-contract.md": _agent_native_loop_body(adapter="opencode", marker_source="opencode_project_command", context_arg='--context-id "${OPENCODE_SESSION_ID:-}"'),
        ".opencode/loopora/references/loopora-recovery-matrix.md": _agent_recovery_matrix(),
        ".opencode/loopora/references/loopora-result-template-guide.md": _agent_result_template_guide("opencode"),
        ".opencode/loopora/references/loopora-role-dispatch-guide.md": _agent_role_dispatch_guide("opencode"),
        ".opencode/agents/loopora-builder.md": _opencode_role_agent("builder"),
        ".opencode/agents/loopora-inspector.md": _opencode_role_agent("inspector"),
        ".opencode/agents/loopora-gatekeeper.md": _opencode_role_agent("gatekeeper"),
        ".opencode/agents/loopora-guide.md": _opencode_role_agent("guide"),
        ".opencode/agents/loopora-orchestrator.md": _opencode_role_agent("orchestrator"),
    }


def _codex_role_agent(role: str) -> str:
    return f"""# {MANAGED_MARKER} version={CODEX_ADAPTER_VERSION} role={role}

name = "loopora-{role}"
description = "{role_agent_description(role)}"
developer_instructions = \"\"\"
{role_agent_body(role).rstrip()}
\"\"\"
"""


def _claude_role_frontmatter(role: str) -> str:
    if role == "orchestrator":
        return """tools: Agent, Task, Read, Write, Bash
maxTurns: 20"""
    if role == "builder":
        return """tools: Read, Glob, Grep, Bash, Write, Edit, MultiEdit
maxTurns: 20"""
    return """tools: Read, Glob, Grep, Bash
maxTurns: 12"""


def _claude_role_agent(role: str) -> str:
    return f"""---
name: loopora-{role}
description: "{role_agent_description(role)}"
{_claude_role_frontmatter(role)}
---

<!-- {CLAUDE_MANAGED_MARKER} version={CLAUDE_ADAPTER_VERSION} role={role} -->

# Loopora {role.capitalize() if role != "gatekeeper" else "GateKeeper"}

{role_agent_body(role)}
"""


def _opencode_role_frontmatter(role: str) -> str:
    if role == "orchestrator":
        return """mode: subagent
permission:
  task:
    "*": deny
    loopora-builder: allow
    loopora-inspector: allow
    loopora-gatekeeper: allow
    loopora-guide: allow"""
    return """mode: subagent
permission:
  task: deny"""


def _opencode_role_agent(role: str) -> str:
    return f"""---
description: "{role_agent_description(role)}"
{_opencode_role_frontmatter(role)}
---

<!-- {OPENCODE_MANAGED_MARKER} version={OPENCODE_ADAPTER_VERSION} role={role} -->

# Loopora {role.capitalize() if role != "gatekeeper" else "GateKeeper"}

{role_agent_body(role)}
"""


def _agent_native_loop_body(*, adapter: str, marker_source: str, context_arg: str = "") -> str:
    return _entry_agent_native_loop_body(adapter=adapter, marker_source=marker_source, context_arg=context_arg)


def _codex_loopora_gen_skill() -> str:
    return _entry_codex_loopora_gen_skill(marker=MANAGED_MARKER, version=CODEX_ADAPTER_VERSION)


def _codex_loopora_loop_skill() -> str:
    return _entry_codex_loopora_loop_skill(marker=MANAGED_MARKER, version=CODEX_ADAPTER_VERSION)


def _claude_loopora_gen_skill() -> str:
    return _entry_claude_loopora_gen_skill(marker=CLAUDE_MANAGED_MARKER, version=CLAUDE_ADAPTER_VERSION)


def _claude_loopora_loop_skill() -> str:
    return _entry_claude_loopora_loop_skill(marker=CLAUDE_MANAGED_MARKER, version=CLAUDE_ADAPTER_VERSION)


def _opencode_loopora_gen_command() -> str:
    return _entry_opencode_loopora_gen_command(marker=OPENCODE_MANAGED_MARKER, version=OPENCODE_ADAPTER_VERSION)


def _opencode_loopora_loop_command() -> str:
    return _entry_opencode_loopora_loop_command(marker=OPENCODE_MANAGED_MARKER, version=OPENCODE_ADAPTER_VERSION)
