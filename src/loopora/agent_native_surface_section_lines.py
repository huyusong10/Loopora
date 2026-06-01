from __future__ import annotations

from loopora.agent_native_surface_line_helpers import _native_surface_kv_line


def _native_surface_packaging_lines(packaging: dict) -> list[str]:
    return _native_surface_kv_line(
        "packaging",
        packaging,
        (
            ("source", "behavior_source"),
            ("entries", "host_entries"),
            ("projections", "projection_policy"),
            ("components", "component_export"),
            ("scope", "install_scope"),
            ("visibility", "entry_visibility"),
            ("shadow", "shadow_policy"),
            ("registry", "registry_policy"),
            ("links", "link_policy"),
            ("bundle", "runtime_bundle"),
            ("manifest", "manifest"),
            ("drift", "drift_check"),
            ("update", "update_policy"),
            ("repair", "repair"),
        ),
    )


def _native_surface_context_loading_lines(context_loading: dict) -> list[str]:
    return _native_surface_kv_line(
        "context loading",
        context_loading,
        (
            ("entry", "entry_prompt"),
            ("summary_first", "summary_first"),
            ("references", "reference_loading"),
            ("full_payload", "full_payload"),
            ("memory", "host_memory"),
            ("memory_store", "memory_store"),
            ("templates", "template_context"),
            ("workflow_kits", "workflow_kits"),
            ("role_catalogs", "role_catalogs"),
            ("compaction", "compaction_context"),
            ("host_context", "host_context"),
            ("catalog", "catalog_context"),
        ),
    )


def _native_surface_health_check_lines(health_check: dict) -> list[str]:
    return _native_surface_kv_line(
        "health check",
        health_check,
        (
            ("adapter", "adapter_check"),
            ("install", "install_check"),
            ("repair", "repair"),
            ("scope", "scope"),
            ("side_effects", "side_effects"),
            ("reload", "host_reload"),
        ),
    )


def _native_surface_session_recovery_lines(session_recovery: dict) -> list[str]:
    return _native_surface_kv_line(
        "session recovery",
        session_recovery,
        (
            ("context_card", "context_card"),
            ("ambiguous", "ambiguous"),
            ("ready", "ready_resume"),
            ("not_ready", "not_ready"),
            ("provider_resume", "provider_session_resume"),
            ("host_sessions", "host_session_discovery"),
            ("checkpoints", "checkpoint_restore"),
        ),
    )


def _native_surface_handoff_protocol_lines(handoff_protocol: dict) -> list[str]:
    return _native_surface_kv_line(
        "handoff",
        handoff_protocol,
        (
            ("channel", "role_channel"),
            ("required", "required_context"),
            ("payload", "payload_policy"),
            ("submit", "submit_gate"),
            ("dispatch_failure", "dispatch_failure"),
            ("parallel", "parallel_dispatch"),
            ("behavioral", "behavioral_activation"),
            ("external", "external_orchestration"),
            ("human", "human_handoff"),
        ),
    )


def _native_surface_permission_boundary_lines(permission_boundary: dict) -> list[str]:
    return _native_surface_kv_line(
        "permission boundary",
        permission_boundary,
        (
            ("owner", "policy_owner"),
            ("loopora", "loopora_policy"),
            ("roles", "role_scope"),
            ("approval", "approval_prompts"),
            ("mode", "mode_switching"),
            ("automation", "automation"),
            ("sandboxes", "sandbox_runners"),
            ("guardrails", "security_guardrails"),
            ("deny", "deny_rules"),
            ("proof", "proof_boundary"),
        ),
    )


def _native_surface_observability_lines(observability: dict) -> list[str]:
    return _native_surface_kv_line(
        "observability",
        observability,
        (
            ("activity", "agent_activity"),
            ("web", "web_view"),
            ("permissions", "permission_prompts"),
            ("hooks", "hook_events"),
            ("hook_protocol", "hook_protocol"),
            ("hook_runners", "hook_runners"),
            ("statusline", "statusline_metrics"),
            ("task_trackers", "task_trackers"),
            ("remote_controls", "remote_controls"),
            ("diagnostic_traces", "diagnostic_traces"),
            ("progress", "progress_signal"),
            ("proof", "proof_signal"),
        ),
    )


def _native_surface_experience_lines(experience_capabilities: dict) -> list[str]:
    return _native_surface_kv_line(
        "experience",
        experience_capabilities,
        (
            ("role_dispatch", "role_dispatch_guidance"),
            ("todo", "todo_guidance"),
            ("user_question", "user_question_guidance"),
            ("trace", "native_trace_optional"),
            ("technical_handoff", "technical_handoff_paths"),
        ),
    )


def _native_surface_tooling_boundary_lines(tooling_boundary: dict) -> list[str]:
    return _native_surface_kv_line(
        "tooling boundary",
        tooling_boundary,
        (
            ("mcp", "mcp_servers"),
            ("tools", "external_tools"),
            ("proof", "tool_outputs"),
        ),
    )


def _native_surface_ownership_lines(ownership_boundary: dict) -> list[str]:
    return _native_surface_kv_line(
        "ownership",
        ownership_boundary,
        (
            ("loopora", "loopora_owned"),
            ("hooks", "managed_hooks"),
            ("host", "host_owned"),
            ("models", "model_policy"),
            ("skills", "skill_policy"),
            ("credentials", "credential_policy"),
            ("repair", "repair_policy"),
        ),
    )
