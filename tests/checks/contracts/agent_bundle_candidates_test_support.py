from __future__ import annotations

from agent_native_v3_helpers import assert_agent_v3_compact_envelope, assert_agent_v3_envelope
from agent_adapter_test_support import (
    AgentBundleCandidateRequest,
    CliRunner,
    LooporaConflictError,
    LooporaError,
    Path,
    TestClient,
    _assert_codex_native_surface_plain,
    _assert_codex_native_surface_summary,
    _assert_invalid_candidate_repair_payload,
    _assert_invalid_candidate_repair_plain_output,
    _assert_invalid_candidate_run_recovery,
    _assert_labeled_loopora_agent_command,
    _assert_loopora_agent_command,
    _assert_missing_candidate_agent_review,
    _assert_not_fit_agent_review,
    _assert_ready_plan_payload,
    _assert_ready_plan_summary,
    _assert_ready_review_projection,
    _assert_web_review_json_payload,
    _assert_web_review_plain_output,
    _error_text,
    _invoke_codex_plan,
    _wait_for_alignment_status,
    _write_ready_bundle,
    alignment_bundle_yaml,
    build_app,
    cli,
    cli_agent_adapter_commands,
    cli_agent_runtime_support,
    json,
    pytest,
    yaml,
)



def _assert_plan_message_required_summary(summary: dict) -> None:
    _assert_codex_native_surface_summary(summary)
    assert summary["ready"] is False
    assert summary["loop_recovery"] == "plan_message_required"
    assert summary["next_plan_command"] == "/loopora-plan"
    assert summary["required_inputs"] == [
        "task_goal",
        "fake_done_risks",
        "required_evidence",
        "judgment_tradeoffs",
    ]
    assert summary["ask_user"].startswith("What long-running task should Loopora govern?")
    assert summary["question_action"]["subagent_policy"].startswith("Do not ask user questions")
    assert summary["question_action"]["recommended_reply_shape"].startswith("Goal:")
    assert summary["question_action"]["decision_impact"].startswith("This answer decides the Loop's task contract")
    assert "fake done would be UI-only deletion" in summary["example_user_reply"]
    assert summary["message_source_policy"].startswith("If the current host user prompt already contains")
    _assert_loopora_agent_command(summary["message_cli_command"], "plan")
    assert "--message" in summary["message_cli_command"]
    assert "--json --compact-json" in summary["message_cli_command"]
    assert summary["next_plan_cli_command"] == summary["message_cli_command"]
    assert summary["first_task_message_example"].startswith("After /loopora-plan, send: Goal:")
    _assert_loopora_agent_command(summary["debug_cli_example_command"], "plan", json_mode=False)
    assert summary["next"] == "Ask the user the ask_user question, then rerun /loopora-plan with the user's task context."

__all__ = [
    'AgentBundleCandidateRequest',
    'CliRunner',
    'LooporaConflictError',
    'LooporaError',
    'Path',
    'TestClient',
    '_assert_codex_native_surface_plain',
    '_assert_codex_native_surface_summary',
    '_assert_invalid_candidate_repair_payload',
    '_assert_invalid_candidate_repair_plain_output',
    '_assert_invalid_candidate_run_recovery',
    '_assert_labeled_loopora_agent_command',
    '_assert_loopora_agent_command',
    '_assert_missing_candidate_agent_review',
    '_assert_not_fit_agent_review',
    '_assert_plan_message_required_summary',
    '_assert_ready_plan_payload',
    '_assert_ready_plan_summary',
    '_assert_ready_review_projection',
    '_assert_web_review_json_payload',
    '_assert_web_review_plain_output',
    '_error_text',
    '_invoke_codex_plan',
    '_wait_for_alignment_status',
    '_write_ready_bundle',
    'alignment_bundle_yaml',
    'assert_agent_v3_compact_envelope',
    'assert_agent_v3_envelope',
    'build_app',
    'cli',
    'cli_agent_adapter_commands',
    'cli_agent_runtime_support',
    'json',
    'pytest',
    'yaml',
]
