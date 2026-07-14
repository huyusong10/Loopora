from __future__ import annotations

from collections.abc import Mapping

from loopora.action_readiness_projection import project_next_action_readiness_contract
from loopora.asset_errors import asset_mutation_error_message


def web_asset_mutation_error_payload(
    exc: BaseException,
    *,
    asset_label: str,
    action: str = "saved",
) -> dict[str, object]:
    message = asset_mutation_error_message(exc, asset_label=asset_label, action=action)
    payload: dict[str, object] = {"error": message}
    if isinstance(exc, OSError | UnicodeError):
        return payload

    asset = _asset_key(asset_label)
    field_errors = _field_errors(message, asset=asset)
    if not field_errors:
        return payload

    fields = [item["field"] for item in field_errors]
    next_actions = [
        {
            "kind": "fix_asset_fields",
            "target": _asset_target(asset),
            "fields": fields,
            "note": _fix_fields_note(asset),
        },
        {
            "kind": "retry_web_asset_save",
            "target": _asset_target(asset),
            "after_action": "fix_asset_fields",
        },
    ]
    payload.update(
        {
            "error_code": "asset_validation_failed",
            "asset": asset,
            "action": action,
            "field_errors": field_errors,
            "web_asset_validation_recovery_summary": {
                "asset": asset,
                "action": action,
                "field_error_count": len(field_errors),
                "fields": fields,
                "next_action_kinds": [item["kind"] for item in next_actions],
            },
            "next_actions": next_actions,
        }
    )
    return project_next_action_readiness_contract(
        payload,
        summary_key="web_asset_validation_recovery_summary",
    )


def web_asset_field_errors(
    exc: BaseException,
    *,
    asset_label: str,
    action: str = "saved",
) -> list[dict[str, str]]:
    payload = web_asset_mutation_error_payload(exc, asset_label=asset_label, action=action)
    field_errors = payload.get("field_errors")
    if not isinstance(field_errors, list):
        return []
    return [
        {"field": str(item.get("field", "")).strip(), "message": str(item.get("message", "")).strip()}
        for item in field_errors
        if isinstance(item, dict) and str(item.get("field", "")).strip() and str(item.get("message", "")).strip()
    ]


def web_asset_field_error_views(
    field_errors: list[Mapping[str, object]] | None,
    *,
    field_labels: Mapping[str, str],
    id_prefix: str,
) -> list[dict[str, str]]:
    views: list[dict[str, str]] = []
    for index, item in enumerate(field_errors or []):
        field = str(item.get("field", "")).strip()
        message = str(item.get("message", "")).strip()
        if not field or not message:
            continue
        views.append(
            {
                "field": field,
                "message": message,
                "label": field_labels.get(field) or field.replace("_", " "),
                "id": f"{id_prefix}-{_field_note_id_component(field)}-{index}",
            }
        )
    return views


def web_asset_field_error_ids(field_errors: list[Mapping[str, object]]) -> dict[str, str]:
    ids: dict[str, str] = {}
    for item in field_errors:
        field = str(item.get("field", "")).strip()
        note_id = str(item.get("id", "")).strip()
        if field and note_id and field not in ids:
            ids[field] = note_id
    return ids


def _field_errors(message: str, *, asset: str) -> list[dict[str, str]]:
    return [{"field": field, "message": message} for field in _asset_error_fields(message, asset=asset)]


def _asset_error_fields(message: str, *, asset: str) -> list[str]:
    text = message.strip().lower()
    fields: list[str] = []
    if "name is required" in text:
        fields.append("name")
    if asset == "role_definition":
        fields.extend(_role_definition_error_fields(text))
    elif asset == "orchestration":
        fields.extend(_orchestration_error_fields(text))
    return _unique_fields(fields)


def _role_definition_error_fields(text: str) -> list[str]:
    fields: list[str] = []
    if "prompt_markdown is required" in text or text.startswith(("prompt markdown", "prompt front matter")):
        fields.append("prompt_markdown")
    if "prompt archetype" in text or "prompt body" in text:
        fields.append("prompt_markdown")
    if "prompt_ref" in text:
        fields.append("prompt_ref")
    if "archetype" in text and "prompt archetype" not in text:
        fields.append("archetype")
    if "executor_kind" in text or "unsupported executor kind" in text:
        fields.append("executor_kind")
    if "executor_mode" in text or "only supports command mode" in text or "custom executor" in text:
        fields.append("executor_mode")
    if "command_cli" in text:
        fields.append("command_cli")
    if "reasoning" in text:
        fields.append("reasoning_effort")
    return fields


def _orchestration_error_fields(text: str) -> list[str]:
    fields: list[str] = [
        field
        for field in ("strategy_json", "workflow_json", "prompt_files_json")
        if text.startswith(f"{field} ")
    ]
    if "unknown workflow preset" in text or "workflow_preset" in text or "strategy_preset" in text:
        fields.append("workflow_preset")
    if _looks_like_strategy_source_error(text):
        fields.append("strategy_json")
    if _looks_like_prompt_file_error(text):
        fields.append("prompt_files_json")
    return fields


def _looks_like_strategy_source_error(text: str) -> bool:
    strategy_fragments = (
        "workflow role",
        "workflow roles",
        "workflow step",
        "workflow steps",
        "workflow control",
        "workflow controls",
        "workflow parallel_group",
        "workflow requires",
        "strategy source",
        "duplicate workflow",
        "role_id",
        "on_pass",
        "action_policy",
        "inherit_session",
    )
    return any(fragment in text for fragment in strategy_fragments)


def _looks_like_prompt_file_error(text: str) -> bool:
    prompt_fragments = (
        "prompt_ref",
        "prompt file",
        "prompt files",
        "prompt artifact",
        "prompt markdown",
        "prompt archetype",
        "prompt front matter",
    )
    return any(fragment in text for fragment in prompt_fragments)


def _unique_fields(fields: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for field in fields:
        if field in seen:
            continue
        seen.add(field)
        unique.append(field)
    return unique


def _field_note_id_component(field: str) -> str:
    normalized = "".join(char if char.isalnum() else "-" for char in field.strip().lower())
    return normalized.strip("-") or "field"


def _asset_key(asset_label: str) -> str:
    return asset_label.strip().lower().replace(" ", "_")


def _asset_target(asset: str) -> str:
    if asset == "orchestration":
        return "web_orchestration_editor"
    if asset == "role_definition":
        return "web_role_definition_editor"
    return "web_asset_editor"


def _fix_fields_note(asset: str) -> str:
    if asset == "orchestration":
        return "Fix the highlighted flow fields before saving this orchestration again."
    if asset == "role_definition":
        return "Fix the highlighted role fields before saving this role definition again."
    return "Fix the highlighted fields before saving again."
