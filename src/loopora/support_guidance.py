from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import shlex

from loopora.fit_guidance import normalize_fit_guidance_language
from loopora.support_guidance_actions import (
    _public_support_command,
    _public_support_target_project_status,
    _public_support_web_support_url,
    _public_support_web_target_args,
    _public_support_workdir_arg,
    _support_action_readiness_kinds,
    _support_next_actions,
)
from loopora.support_guidance_constants import (
    PRIVATE_SECURITY_REPORT_URL,
    SECURITY_POLICY_URL,
    SUPPORT_DOCUMENT_URL,
    SUPPORT_FALLBACK_PUBLIC_PASTE_ITEMS,
    SUPPORT_HELP_EPILOG as SUPPORT_HELP_EPILOG,
    SUPPORT_IDENTITY_PUBLIC_PASTE_ITEMS,
    SUPPORT_LOCAL_ONLY_ITEMS,
    SUPPORT_PREFERRED_PUBLIC_PASTE_ITEMS,
    SUPPORT_PUBLIC_PASTE_ITEMS,
    SUPPORT_REDACTION_ITEMS,
    SUPPORT_SCHEMA_VERSION,
    SUPPORT_WORKDIR_PLACEHOLDER,
)
from loopora.support_guidance_projection import _project_support_next_action_contract
from loopora.support_guidance_routes import support_issue_routes as _support_issue_routes
from loopora.support_guidance_text import (
    support_command_blocker_label as support_command_blocker_label,
    support_command_status_lines as support_command_status_lines,
    support_local_command_lines as support_local_command_lines,
    support_local_only_items as support_local_only_items,
    support_payload_language as support_payload_language,
    support_posting_guidance_text as support_posting_guidance_text,
    support_public_paste_items as support_public_paste_items,
    support_redaction_items as support_redaction_items,
    support_target_project_lines as support_target_project_lines,
    support_target_project_state_lines as support_target_project_state_lines,
    support_target_project_status_label as support_target_project_status_label,
    support_text as support_text,
    support_web_lines as support_web_lines,
)


def normalize_support_guidance_language(language: str) -> str:
    return normalize_fit_guidance_language(language)


def public_support_payload(
    *,
    workdir: Path | str | None = None,
    language: str = "en",
    web_host: str | None = None,
    web_port: int | str | None = None,
) -> dict[str, object]:
    support_language = normalize_support_guidance_language(language)
    workdir_arg = _public_support_workdir_arg(workdir)
    target_project_status = _public_support_target_project_status(workdir)
    web_target_args = _public_support_web_target_args(web_host=web_host, web_port=web_port)
    web_support_url = _public_support_web_support_url(web_host=web_host, web_port=web_port, workdir=workdir)
    command_fields_are_placeholders = workdir_arg == shlex.quote(SUPPORT_WORKDIR_PLACEHOLDER)
    target_project_required = command_fields_are_placeholders
    command_field_blockers = ["target_project_required"] if target_project_required else []
    command_fields_executable = not command_field_blockers
    public_doctor_command = _public_support_command(f"loopora doctor --public-json{web_target_args} --workdir {workdir_arg}")
    issue_routes = _support_issue_routes()
    commands = {
        "public_issue_bundle": _public_support_command(f"loopora support --public-issue-bundle{web_target_args} --workdir {workdir_arg}"),
        "public_doctor": f"{public_doctor_command} || true",
        "version": _public_support_command("loopora --version"),
        "version_json": _public_support_command("loopora version --json"),
    }
    next_actions = _support_next_actions(
        commands=commands,
        command_fields_executable=command_fields_executable,
        target_project_required=target_project_required,
        language=support_language,
        web_target_args=web_target_args,
    )
    ready_action_kinds, blocked_action_kinds = _support_action_readiness_kinds(next_actions)
    payload: dict[str, object] = {
        "schema_version": SUPPORT_SCHEMA_VERSION,
        "language": support_language,
        "target_project_required": target_project_required,
        "command_fields_are_placeholders": command_fields_are_placeholders,
        "command_fields_executable": command_fields_executable,
        "command_field_blockers": command_field_blockers,
        "command_fields_are_local_only": True,
        "command_fields_public_pasteable": False,
        "target_project_status": target_project_status,
        "target_project_setup_ready": target_project_status == "ready",
        "target_project_report_only": command_fields_executable and target_project_status != "ready",
        "workdir_arg": workdir_arg,
        "support_summary": {
            "scope": "best_effort",
            "response_time": "no_guarantee",
            "local_first": True,
            "public_report_redacted": True,
            "target_project_required": target_project_required,
            "target_project_status": target_project_status,
            "target_project_setup_ready": target_project_status == "ready",
            "target_project_report_only": command_fields_executable and target_project_status != "ready",
            "command_fields_are_placeholders": command_fields_are_placeholders,
            "command_fields_executable": command_fields_executable,
            "command_field_blockers": command_field_blockers,
            "command_fields_are_local_only": True,
            "command_fields_public_pasteable": False,
            "issue_route_kinds": [route["kind"] for route in issue_routes],
            "next_action_kinds": [action["kind"] for action in next_actions],
            "ready_next_action_kinds": ready_action_kinds,
            "blocked_next_action_kinds": blocked_action_kinds,
        },
        "commands": commands,
        "next_actions": next_actions,
        "posting_guidance": {
            "run_commands_locally": True,
            "run_ready_commands_locally": True,
            "preview_command_fields_require_target_project": target_project_required,
            "paste_outputs_not_command_lines": True,
            "support_json_is_route_metadata": True,
            "command_fields_are_local_only": True,
            "preferred_public_output": "public_issue_bundle_output",
            "fallback_public_outputs": SUPPORT_FALLBACK_PUBLIC_PASTE_ITEMS,
            "identity_public_outputs": SUPPORT_IDENTITY_PUBLIC_PASTE_ITEMS,
            "pasteable_public_outputs": SUPPORT_PUBLIC_PASTE_ITEMS,
        },
        "public_issue_materials": {
            "preferred": SUPPORT_PREFERRED_PUBLIC_PASTE_ITEMS,
            "fallback": SUPPORT_FALLBACK_PUBLIC_PASTE_ITEMS,
            "identity": SUPPORT_IDENTITY_PUBLIC_PASTE_ITEMS,
            "pasteable": SUPPORT_PUBLIC_PASTE_ITEMS,
            "local_only": SUPPORT_LOCAL_ONLY_ITEMS,
            "redact_or_remove": SUPPORT_REDACTION_ITEMS,
        },
        "docs": {
            "support": "SUPPORT.md",
            "security": "SECURITY.md",
            "contributing": "CONTRIBUTING.md",
        },
        "links": {
            "support": SUPPORT_DOCUMENT_URL,
            "security_policy": SECURITY_POLICY_URL,
            "private_security_report": PRIVATE_SECURITY_REPORT_URL,
        },
        "local_links": {"web_support": web_support_url} if web_support_url else {},
        "security_reporting": {
            "policy_url": SECURITY_POLICY_URL,
            "private_report_url": PRIVATE_SECURITY_REPORT_URL,
            "public_fallback": "private_channel_request_only",
            "public_fallback_no_sensitive_details": True,
        },
        "issue_routes": issue_routes,
        "redaction": SUPPORT_REDACTION_ITEMS,
    }
    _project_support_next_action_contract(payload)
    return payload


def public_support_guidance_lines(payload: Mapping[str, object]) -> list[str]:
    from loopora.support_guidance_output import public_support_guidance_lines as render_public_support_guidance_lines

    return render_public_support_guidance_lines(payload)


def support_public_issue_bundle_text(public_doctor_payload: Mapping[str, object], *, language: str = "en") -> str:
    from loopora.support_issue_bundle import support_public_issue_bundle_text as render_support_public_issue_bundle_text

    return render_support_public_issue_bundle_text(public_doctor_payload, language=language)


def support_public_issue_bundle_summary_lines(public_doctor_payload: Mapping[str, object], *, language: str = "en") -> list[str]:
    from loopora.support_issue_bundle import (
        support_public_issue_bundle_summary_lines as render_support_public_issue_bundle_summary_lines,
    )

    return render_support_public_issue_bundle_summary_lines(public_doctor_payload, language=language)


def support_public_issue_bundle_identity(public_doctor_payload: Mapping[str, object]) -> str:
    from loopora.support_issue_bundle import support_public_issue_bundle_identity as render_support_public_issue_bundle_identity

    return render_support_public_issue_bundle_identity(public_doctor_payload)
