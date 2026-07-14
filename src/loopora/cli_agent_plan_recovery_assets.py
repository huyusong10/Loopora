from __future__ import annotations

from loopora.system_prompt_assets import load_system_prompt_asset


def _agent_native_recovery_asset(asset_ref: str) -> str:
    return load_system_prompt_asset(f"agent_native/{asset_ref}").strip()


def _agent_native_recovery_asset_lines(asset_ref: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in _agent_native_recovery_asset(asset_ref).splitlines() if line.strip())


REPAIR_CLI_COMMAND_POLICY = _agent_native_recovery_asset("repair-cli-command-policy.md")
REPAIR_REFERENCE = _agent_native_recovery_asset("repair-reference.md")
REPAIR_FORBIDDEN_ACTIONS = _agent_native_recovery_asset_lines("repair-forbidden-actions.md")
REPAIR_NEXT_ACTION = _agent_native_recovery_asset("repair-next-action.md")
REPAIR_NEXT_REPAIR_STEP = _agent_native_recovery_asset("repair-next-repair-step.md")
ALIGNMENT_QUESTION_SUBAGENT_POLICY = _agent_native_recovery_asset("alignment-question-subagent-policy.md")
ALIGNMENT_QUESTION_NEXT_MESSAGE_POLICY = _agent_native_recovery_asset("alignment-question-next-message-policy.md")
ALIGNMENT_QUESTION_NEXT_STEP = _agent_native_recovery_asset("alignment-question-next-step.md")
NEXT_PLAN_CLI_COMMAND_POLICY = "fallback_for_non_interactive_agents; primary path is preview_url/Web review or an explicit user decision"
READY_RUN_NEXT_STEP = _agent_native_recovery_asset("ready-run-next-step.md")
CONTEXT_CARD_REPAIR_NEXT_ACTION = "Fix write access to the target project's .loopora agent state, then rerun /loopora-plan in this same Agent session."
