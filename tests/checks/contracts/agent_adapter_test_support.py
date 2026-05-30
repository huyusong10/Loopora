from __future__ import annotations

import hashlib
import json
import shlex
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner
import yaml

from loopora import cli
from loopora import cli_agent_adapter_commands
from loopora import cli_agent_native
from loopora import cli_agent_runtime_support
import loopora.agent_adapters as agent_adapters
import loopora.agent_web as agent_web
import loopora.service_agent_native as service_agent_native
from loopora.executor_fake_payloads import alignment_bundle_yaml
from loopora.service_agent_adapters import AgentBundleCandidateRequest
from loopora.service_agent_native import AgentNativeStepClaimRequest, AgentNativeStepSubmitRequest, ServiceAgentNativeMixin
from loopora.service_types import LooporaConflictError, LooporaError
from loopora.run_artifacts import RunArtifactLayout, read_jsonl
from loopora.utils import append_jsonl
from loopora.web import build_app
from loopora.workflows import WorkflowError
from agent_adapter_expected import (
    EXPECTED_NATIVE_CONTEXT_LOADING,
    EXPECTED_NATIVE_OBSERVABILITY,
    EXPECTED_NATIVE_PACKAGING,
    EXPECTED_NATIVE_PERMISSION_BOUNDARY,
    EXPECTED_NATIVE_TOOLING_BOUNDARY,
)

from agent_adapter_test_common import (
    _assert_expected_mapping_values,
    _error_text,
    _labeled_value,
    _assert_loopora_agent_command,
    _assert_labeled_loopora_agent_command,
    _assert_loopora_cli_command,
    _assert_recovery_choice_has_copyable_commands,
    _assert_not_ready_recovery_choice_routes_to_plan,
    _assert_non_runnable_recovery_choice_routes_to_plan,
    _assert_recovery_choice_has_status_hint,
    _candidate_digest,
    _ready_candidate_digest,
    _wait_for_alignment_status,
    _assert_cli_handoff_contract_paths,
    _assert_cli_list,
    _assert_output_contains,
    _assert_native_context_loading,
)

from agent_adapter_test_surface import (
    _assert_codex_native_surface_summary,
    _assert_codex_native_surface_runtime_boundaries,
    _assert_codex_native_surface_ownership,
    _assert_codex_native_surface_plain,
    _assert_codex_native_surface_plain_runtime,
    _assert_codex_native_surface_plain_ownership,
)

from agent_adapter_test_plan import (
    _assert_plan_repair_retry_text,
    _assert_plan_repair_retry_payload,
    _invoke_codex_plan,
    _assert_web_review_plain_output,
    _assert_web_review_json_payload,
    _write_ready_bundle,
    _assert_ready_plan_summary,
    _assert_ready_plan_payload,
    _assert_ready_review_projection,
    _assert_invalid_candidate_repair_plain_output,
    _assert_invalid_candidate_repair_payload,
    _assert_invalid_candidate_run_recovery,
    _assert_missing_candidate_agent_review,
    _assert_not_fit_agent_review,
)

from agent_adapter_test_submit import (
    _write_agent_submit_repair_fixture,
    _agent_submit_repair_active_step_view,
    _stale_builder_result_wrapper,
    _bad_ref_inspector_result_wrapper,
    _invoke_codex_submit,
    _assert_stale_submit_repair_payload,
    _assert_bad_ref_submit_repair_payload,
    _assert_plain_bad_ref_submit_repair,
)

from agent_adapter_test_runtime import (
    _assert_terminal_recovery_choice,
    _assert_ambiguous_agent_recovery_choices,
    _alignment_bundle_yaml_with_gatekeeper_control,
    _alignment_bundle_yaml_with_peer_visible_parallel_review_inputs,
    _agent_native_step_output,
    _agent_native_rejected_gatekeeper_output,
    _drive_agent_native_until_archetype,
    _agent_native_host_dispatch,
    _drive_agent_native_run_to_success,
)

from agent_adapter_test_install import (
    _codex_skill_paths,
    _claude_skill_paths,
    _opencode_command_paths,
    _claude_settings_has_loopora_session_hook,
    _assert_claude_gen_entry,
    _assert_claude_loop_entry,
    _assert_claude_agent_prompts,
    _assert_claude_manifest,
    _assert_claude_managed_install,
    _assert_opencode_managed_install,
    _assert_codex_managed_install,
    _assert_codex_role_agent_files,
    _assert_loop_entry_native_run_contract,
    _assert_codex_manifest,
)

from agent_adapter_test_observation import (
    _assert_agent_run_summary_for_started_run,
    _assert_agent_run_summary_continuation,
    _assert_agent_native_observation_current_step,
    _assert_agent_native_observation_artifacts,
    _assert_agent_native_observation_step_view,
    _assert_agent_native_observation_template,
    _assert_step_view_submit_hint_uses_safe_filled_result_path,
    _assert_result_template_dispatch,
    _assert_result_template_contract_targets,
    _assert_submit_hint_command_requests_json,
    _write_agent_native_cli_contract,
    _assert_agent_native_cli_output,
    _assert_agent_run_json_summary_reports_missing_dispatch,
    _assert_cli_dispatch_unavailable,
)

from agent_adapter_test_next import (
    _assert_agent_next_json_summary,
    _assert_agent_next_step_json_summary,
    _assert_agent_work_panel_summary,
    _expected_agent_next_todo_items,
)

__all__ = [
    "EXPECTED_NATIVE_CONTEXT_LOADING",
    "EXPECTED_NATIVE_OBSERVABILITY",
    "EXPECTED_NATIVE_PACKAGING",
    "EXPECTED_NATIVE_PERMISSION_BOUNDARY",
    "EXPECTED_NATIVE_TOOLING_BOUNDARY",
    "AgentBundleCandidateRequest",
    "AgentNativeStepClaimRequest",
    "AgentNativeStepSubmitRequest",
    "CliRunner",
    "LooporaConflictError",
    "LooporaError",
    "Path",
    "RunArtifactLayout",
    "ServiceAgentNativeMixin",
    "TestClient",
    "WorkflowError",
    "_agent_native_host_dispatch",
    "_agent_native_rejected_gatekeeper_output",
    "_agent_native_step_output",
    "_agent_submit_repair_active_step_view",
    "_alignment_bundle_yaml_with_gatekeeper_control",
    "_alignment_bundle_yaml_with_peer_visible_parallel_review_inputs",
    "_assert_agent_native_cli_output",
    "_assert_agent_native_observation_artifacts",
    "_assert_agent_native_observation_current_step",
    "_assert_agent_native_observation_step_view",
    "_assert_agent_native_observation_template",
    "_assert_agent_next_json_summary",
    "_assert_agent_next_step_json_summary",
    "_assert_agent_run_json_summary_reports_missing_dispatch",
    "_assert_agent_run_summary_continuation",
    "_assert_agent_run_summary_for_started_run",
    "_assert_agent_work_panel_summary",
    "_assert_ambiguous_agent_recovery_choices",
    "_assert_bad_ref_submit_repair_payload",
    "_assert_claude_agent_prompts",
    "_assert_claude_gen_entry",
    "_assert_claude_loop_entry",
    "_assert_claude_managed_install",
    "_assert_claude_manifest",
    "_assert_cli_dispatch_unavailable",
    "_assert_cli_handoff_contract_paths",
    "_assert_cli_list",
    "_assert_codex_managed_install",
    "_assert_codex_manifest",
    "_assert_codex_native_surface_ownership",
    "_assert_codex_native_surface_plain",
    "_assert_codex_native_surface_plain_ownership",
    "_assert_codex_native_surface_plain_runtime",
    "_assert_codex_native_surface_runtime_boundaries",
    "_assert_codex_native_surface_summary",
    "_assert_codex_role_agent_files",
    "_assert_expected_mapping_values",
    "_assert_invalid_candidate_repair_payload",
    "_assert_invalid_candidate_repair_plain_output",
    "_assert_invalid_candidate_run_recovery",
    "_assert_labeled_loopora_agent_command",
    "_assert_loop_entry_native_run_contract",
    "_assert_loopora_agent_command",
    "_assert_loopora_cli_command",
    "_assert_missing_candidate_agent_review",
    "_assert_native_context_loading",
    "_assert_non_runnable_recovery_choice_routes_to_plan",
    "_assert_not_fit_agent_review",
    "_assert_not_ready_recovery_choice_routes_to_plan",
    "_assert_opencode_managed_install",
    "_assert_output_contains",
    "_assert_plain_bad_ref_submit_repair",
    "_assert_plan_repair_retry_payload",
    "_assert_plan_repair_retry_text",
    "_assert_ready_plan_payload",
    "_assert_ready_plan_summary",
    "_assert_ready_review_projection",
    "_assert_recovery_choice_has_copyable_commands",
    "_assert_recovery_choice_has_status_hint",
    "_assert_result_template_contract_targets",
    "_assert_result_template_dispatch",
    "_assert_stale_submit_repair_payload",
    "_assert_step_view_submit_hint_uses_safe_filled_result_path",
    "_assert_submit_hint_command_requests_json",
    "_assert_terminal_recovery_choice",
    "_assert_web_review_json_payload",
    "_assert_web_review_plain_output",
    "_bad_ref_inspector_result_wrapper",
    "_candidate_digest",
    "_claude_settings_has_loopora_session_hook",
    "_claude_skill_paths",
    "_codex_skill_paths",
    "_drive_agent_native_run_to_success",
    "_drive_agent_native_until_archetype",
    "_error_text",
    "_expected_agent_next_todo_items",
    "_invoke_codex_plan",
    "_invoke_codex_submit",
    "_labeled_value",
    "_opencode_command_paths",
    "_ready_candidate_digest",
    "_stale_builder_result_wrapper",
    "_wait_for_alignment_status",
    "_write_agent_native_cli_contract",
    "_write_agent_submit_repair_fixture",
    "_write_ready_bundle",
    "agent_adapters",
    "agent_web",
    "alignment_bundle_yaml",
    "append_jsonl",
    "build_app",
    "cli",
    "cli_agent_adapter_commands",
    "cli_agent_native",
    "cli_agent_runtime_support",
    "hashlib",
    "json",
    "pytest",
    "read_jsonl",
    "service_agent_native",
    "shlex",
    "time",
    "yaml",
]
