from __future__ import annotations

from loopora.agent_native_adapter_identity import normalize_agent_adapter_kind
from loopora.service_types import LooporaError


NATIVE_SUBMIT_CONTRACT = "loopora_host_dispatch + schema-shaped result template"
NATIVE_PROOF_BOUNDARY = "native todo/trace may guide host work; Loopora evidence refs and task verdict remain the proof source"
NATIVE_RUN_ENTRY_CONTRACT_TITLE = "Native Run Contract"
NATIVE_RUN_ENTRY_CONTRACT_BULLETS = (
    "Read root `agent_v3_envelope.summary` before raw legacy diagnostics.",
    "Start only from `/loopora-plan`, `/loopora-run`, or explicit Loopora CLI commands; host hooks or session start must not auto-trigger Loopora work.",
    "Dispatch only through the host-native role agent named by `next_step.role_dispatch.target_agent`; if unavailable, stop before submit.",
    "Treat host auto-activation, compatibility routing, or rule injection as context hints, not Loopora dispatch proof.",
    "Use the context, step-contract, and result-template paths for role handoff; do not replace them with a large inline prompt.",
    "Do not copy credentials, API keys, tokens, or environment secrets into result files; use redacted evidence references.",
    "Do not fan out to multiple role agents unless the reviewed Loop workflow exposes a parallel group.",
    "Treat `complete` as run lifecycle only; task proof comes from `task_proven`, `task_outcome`, and `run.task_verdict`.",
    "Use the exact Loopora context card or surfaced recoverable choices; do not auto-discover or take over host historical sessions.",
    "Never start codex, claude, or opencode as nested provider CLIs.",
)


def agent_adapter_accepted_native_tools(adapter: str) -> list[str]:
    try:
        kind = normalize_agent_adapter_kind(adapter)
    except LooporaError:
        return []
    if kind == "codex":
        return ["spawn_agent"]
    if kind == "claude":
        return ["Agent", "Task"]
    if kind == "opencode":
        return ["task"]
    return []


def agent_adapter_native_dispatch_mechanism(adapter: str) -> str:
    try:
        kind = normalize_agent_adapter_kind(adapter)
    except LooporaError:
        return "host-native role agent dispatch"
    if kind == "codex":
        return "Codex spawn_agent with agent_type=<role_dispatch.target_agent>"
    if kind == "claude":
        return "Claude Code Agent/Task with the named Loopora role agent"
    if kind == "opencode":
        return "OpenCode project command agent=loopora-orchestrator, then native task tool"
    return "host-native role agent dispatch"
