from __future__ import annotations

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.specs import (
    SPEC_FILE_DIRECTORY_ERROR,
    SPEC_FILE_EXISTS_ERROR,
    SPEC_FILE_INIT_ERROR,
    SPEC_FILE_SAVE_ERROR,
)


def web_spec_output_recovery_payload(
    *,
    action: str,
    validation_error: str,
) -> dict[str, object]:
    actions = _web_spec_output_recovery_actions(action)
    payload: dict[str, object] = {
        "ok": False,
        "error": validation_error,
        "resource_recovery": "invalid_spec_output_target",
        "status": "blocked_by_spec_output",
        "surface": "web_spec_document",
        "resource": "Markdown spec",
        "action": action,
        "output_state": _web_spec_output_state(validation_error),
        "validation_error": validation_error,
        "web_spec_output_recovery_summary": {
            "ready": False,
            "status": "blocked_by_spec_output",
            "surface": "web_spec_document",
            "resource": "Markdown spec",
            "action": action,
            "output_state": _web_spec_output_state(validation_error),
            "next_action_kinds": _web_spec_action_kinds(actions),
        },
        "next_actions": actions,
    }
    return project_next_action_readiness_contract(payload, summary_key="web_spec_output_recovery_summary")


def _web_spec_output_state(validation_error: str) -> str:
    if validation_error == SPEC_FILE_DIRECTORY_ERROR:
        return "directory"
    if validation_error == SPEC_FILE_EXISTS_ERROR:
        return "exists"
    if validation_error == "spec parent directory does not exist":
        return "missing_parent"
    if validation_error in {SPEC_FILE_INIT_ERROR, SPEC_FILE_SAVE_ERROR, "spec file could not be saved"}:
        return "write_failed"
    return "unavailable"


def _web_spec_output_recovery_actions(action: str) -> list[dict[str, object]]:
    if action == "init":
        return [
            {
                "kind": "choose_spec_output_file",
                "target": "web_spec_init",
            },
            {
                "kind": "retry_web_spec_init",
                "target": "web_spec_init",
                "after_action": "choose_spec_output_file",
            },
            {
                "kind": "render_spec_template",
                "target": "web_spec_template",
            },
        ]
    return [
        {
            "kind": "choose_spec_output_file",
            "target": "web_spec_editor",
        },
        {
            "kind": "retry_web_spec_save",
            "target": "web_spec_editor",
            "after_action": "choose_spec_output_file",
        },
        {
            "kind": "validate_spec_content",
            "target": "web_spec_editor",
        },
    ]


def _web_spec_action_kinds(actions: list[dict[str, object]]) -> list[str]:
    return [str(action.get("kind") or "").strip() for action in actions if str(action.get("kind") or "").strip()]
