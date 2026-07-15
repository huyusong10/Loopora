from __future__ import annotations

from loopora.agent_adapter_claude_hook import CLAUDE_SESSION_CONTEXT_RELATIVE_PATH
from loopora.agent_adapter_host_config import (
    CLAUDE_SESSION_HOOK_RELATIVE_PATH,
    claude_session_additional_context as _claude_session_additional_context,
    claude_session_hook_script as _claude_session_hook_script,
)
from loopora.service_types import LooporaError
from loopora.system_prompt_assets import render_system_prompt_asset



from loopora.residual_risk_prompt_guidance import AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE

from loopora.system_prompt_assets import load_system_prompt_asset





from loopora.residual_risk_prompt_guidance import (
    GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
    GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE,
)

from loopora.proof_command_prompt_guidance import (
    INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE,
    PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
)


_ROLE_DESCRIPTION_ASSETS = {
    "builder": "agent_native/role-description-builder.md",
    "inspector": "agent_native/role-description-inspector.md",
    "gatekeeper": "agent_native/role-description-gatekeeper.md",
    "guide": "agent_native/role-description-guide.md",
    "orchestrator": "agent_native/role-description-orchestrator.md",
}

def role_agent_description(role: str) -> str:
    asset_ref = _ROLE_DESCRIPTION_ASSETS.get(role, "agent_native/role-description-generic.md")
    return load_system_prompt_asset(asset_ref).strip()

def role_agent_body(role: str) -> str:
    if role == "orchestrator":
        return render_system_prompt_asset(
            "agent_native/role-agent-orchestrator.md",
            {"PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE": PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE},
        )
    label = role.capitalize() if role != "gatekeeper" else "GateKeeper"
    gatekeeper_upstream_evidence_guidance = _gatekeeper_upstream_evidence_guidance(role)
    gatekeeper_dynamic_check_guidance = _gatekeeper_dynamic_check_guidance(role)
    inspector_dynamic_check_guidance = _inspector_dynamic_check_guidance(role)
    return render_system_prompt_asset(
        "agent_native/role-agent-standard.md",
        {
            "label": label,
            "gatekeeper_upstream_evidence_guidance": gatekeeper_upstream_evidence_guidance,
            "GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE": GATEKEEPER_RESIDUAL_RISK_PROMPT_GUIDANCE,
            "gatekeeper_dynamic_check_guidance": gatekeeper_dynamic_check_guidance,
            "inspector_dynamic_check_guidance": inspector_dynamic_check_guidance,
            "PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE": PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE,
        },
    )

def _gatekeeper_upstream_evidence_guidance(role: str) -> str:
    if role != "gatekeeper":
        return ""
    return GATEKEEPER_UPSTREAM_EVIDENCE_PROMPT_GUIDANCE

def _gatekeeper_dynamic_check_guidance(role: str) -> str:
    if role != "gatekeeper":
        return ""
    return load_system_prompt_asset("agent_native/gatekeeper-dynamic-check.md").strip() + "\n\n"

def _inspector_dynamic_check_guidance(role: str) -> str:
    if role != "inspector":
        return ""
    return (
        render_system_prompt_asset(
            "agent_native/inspector-dynamic-check.md",
            {"INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE": INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE},
        ).strip()
        + "\n\n"
    )

def agent_native_dispatch_guidance(adapter: str) -> str:
    if adapter == "codex":
        return "\n" + load_system_prompt_asset("agent_native/dispatch-guidance-codex.md").strip() + "\n"
    if adapter == "claude":
        return "\n" + load_system_prompt_asset("agent_native/dispatch-guidance-claude.md").strip() + "\n"
    if adapter == "opencode":
        return "\n" + load_system_prompt_asset("agent_native/dispatch-guidance-opencode.md").strip() + "\n"
    return ""

def _run_contract_values(*, adapter: str, marker_source: str, context_arg: str = "", context_bits: str = "") -> dict[str, str]:
    resolved_context_bits = context_bits or (f" {context_arg}" if context_arg else "")
    return {
        "adapter": adapter,
        "marker_source": marker_source,
        "context_bits": resolved_context_bits,
        "dispatch_guidance": agent_native_dispatch_guidance(adapter).rstrip(),
    }

def agent_run_section_overview(*, adapter: str, marker_source: str, context_bits: str) -> str:
    contract = render_system_prompt_asset(
        "agent_native/run-contract.md",
        _run_contract_values(adapter=adapter, marker_source=marker_source, context_bits=context_bits),
    )
    overview = contract.split("## Detailed Contract", 1)[0]
    return overview.removeprefix("# Loopora Run Contract\n\n").rstrip()

def agent_native_loop_body(*, adapter: str, marker_source: str, context_arg: str = "") -> str:
    return render_system_prompt_asset(
        "agent_native/run-contract.md",
        _run_contract_values(adapter=adapter, marker_source=marker_source, context_arg=context_arg),
    )

def agent_native_run_entry_contract() -> str:
    return load_system_prompt_asset("agent_native/run-entry-contract.md")

_entry_agent_native_loop_body = agent_native_loop_body

def _render_entry_template(asset_ref: str, *, marker: str, version: int) -> str:
    return render_system_prompt_asset(
        asset_ref,
        {
            "marker": marker,
            "version": version,
            "run_entry_contract": agent_native_run_entry_contract().rstrip(),
        },
    )

def codex_loopora_gen_skill(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-codex-plan.md", marker=marker, version=version)

def codex_loopora_loop_skill(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-codex-run.md", marker=marker, version=version)

def claude_loopora_gen_skill(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-claude-plan.md", marker=marker, version=version)

def claude_loopora_loop_skill(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-claude-run.md", marker=marker, version=version)

def opencode_loopora_gen_command(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-opencode-plan.md", marker=marker, version=version)

def opencode_loopora_loop_command(*, marker: str, version: int) -> str:
    return _render_entry_template("agent_native/entry-opencode-run.md", marker=marker, version=version)

_entry_claude_loopora_gen_skill = claude_loopora_gen_skill
_entry_claude_loopora_loop_skill = claude_loopora_loop_skill
_entry_codex_loopora_gen_skill = codex_loopora_gen_skill
_entry_codex_loopora_loop_skill = codex_loopora_loop_skill
_entry_opencode_loopora_gen_command = opencode_loopora_gen_command
_entry_opencode_loopora_loop_command = opencode_loopora_loop_command

def agent_plan_contract(
    adapter: str,
    adapter_label: str,
    marker_source: str,
    *,
    context_arg: str = "",
    supports_arguments: bool = False,
) -> str:
    context_bits = f" {context_arg}" if context_arg else ""
    argument_asset = "agent_native/plan-arguments-host.md" if supports_arguments else "agent_native/plan-arguments-user.md"
    return render_system_prompt_asset(
        "agent_native/plan-contract.md",
        {
            "adapter": adapter,
            "adapter_label": adapter_label,
            "marker_source": marker_source,
            "context_bits": context_bits,
            "argument_text": load_system_prompt_asset(argument_asset).strip(),
            "AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE": AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE,
        },
    )

def agent_recovery_matrix() -> str:
    return load_system_prompt_asset("agent_native/recovery-matrix.md")

def agent_result_template_guide(adapter: str) -> str:
    return render_system_prompt_asset("agent_native/result-template-guide.md", {"adapter": adapter})

def agent_role_dispatch_guide(adapter: str) -> str:
    dispatch_guidance = agent_native_dispatch_guidance(adapter).strip()
    extra = f"\n\n{dispatch_guidance}" if dispatch_guidance else ""
    return render_system_prompt_asset(
        "agent_native/role-dispatch-guide.md",
        {
            "adapter": adapter,
            "dispatch_guidance_extra": extra,
        },
    )

_agent_plan_contract = agent_plan_contract
_agent_recovery_matrix = agent_recovery_matrix
_agent_result_template_guide = agent_result_template_guide
_agent_role_dispatch_guide = agent_role_dispatch_guide

ADAPTER_MANAGED_SCHEMA_VERSION = 3
ADAPTER_VERSION = 73
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
        CLAUDE_SESSION_CONTEXT_RELATIVE_PATH: _claude_session_additional_context(),
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
    return _render_managed_role_agent(
        "agent_native/managed-role-codex.md",
        role=role,
        marker=MANAGED_MARKER,
        version=CODEX_ADAPTER_VERSION,
    )


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
    return _render_managed_role_agent(
        "agent_native/managed-role-claude.md",
        role=role,
        marker=CLAUDE_MANAGED_MARKER,
        version=CLAUDE_ADAPTER_VERSION,
        frontmatter=_claude_role_frontmatter(role),
    )


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
    return _render_managed_role_agent(
        "agent_native/managed-role-opencode.md",
        role=role,
        marker=OPENCODE_MANAGED_MARKER,
        version=OPENCODE_ADAPTER_VERSION,
        frontmatter=_opencode_role_frontmatter(role),
    )


def _render_managed_role_agent(
    asset_ref: str,
    *,
    role: str,
    marker: str,
    version: int,
    frontmatter: str = "",
) -> str:
    return render_system_prompt_asset(
        asset_ref,
        {
            "marker": marker,
            "version": version,
            "role": role,
            "description": role_agent_description(role),
            "frontmatter": frontmatter,
            "label": role.capitalize() if role != "gatekeeper" else "GateKeeper",
            "body": role_agent_body(role).rstrip(),
        },
    )


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
