from __future__ import annotations

from functools import lru_cache
from string import Formatter
from typing import Any

from loopora.alignment_guidance import load_alignment_guidance_assets

LOCALIZED_BASE_BUNDLE_OVERRIDES_ASSET_NAME = "localized-base-bundle-overrides.yml"


def apply_localized_base_bundle_overrides(
    bundle: dict,
    *,
    locale: str,
    context: dict[str, str],
) -> None:
    overrides = localized_base_bundle_overrides(locale, context=context)
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    workflow = bundle.get("workflow") if isinstance(bundle.get("workflow"), dict) else {}
    metadata["name"] = overrides["metadata_name"]
    metadata["description"] = overrides["metadata_description"]
    loop["name"] = overrides["loop_name"]
    bundle["metadata"] = metadata
    bundle["loop"] = loop
    bundle["collaboration_summary"] = overrides["collaboration_summary"]
    spec["markdown"] = overrides["spec_markdown"]
    bundle["spec"] = spec
    workflow["collaboration_intent"] = overrides["workflow_collaboration_intent"]
    bundle["workflow"] = workflow
    _apply_role_overrides(bundle, overrides["roles"])


def localized_base_bundle_overrides(locale: str, *, context: dict[str, str]) -> dict[str, Any]:
    overrides = _localized_base_bundle_overrides_asset().get(str(locale or ""))
    if not isinstance(overrides, dict):
        raise ValueError(f"missing localized base bundle overrides: {locale}")
    rendered = _localized_base_bundle_override_fields(str(locale or ""), overrides)
    _render_localized_base_bundle_overrides(rendered, context)
    return rendered


@lru_cache
def _localized_base_bundle_overrides_asset() -> dict[str, dict[str, Any]]:
    asset = load_alignment_guidance_assets().localized_base_bundle_overrides
    if asset.get("schema_version") != 1 or not isinstance(asset.get("locales"), dict):
        raise ValueError(f"{LOCALIZED_BASE_BUNDLE_OVERRIDES_ASSET_NAME} must define schema_version 1 and locales")
    return {str(locale): _localized_base_bundle_override_fields(str(locale), fields) for locale, fields in asset["locales"].items()}


def _localized_base_bundle_override_fields(locale: str, fields: Any) -> dict[str, Any]:
    if not isinstance(fields, dict):
        raise ValueError(f"{LOCALIZED_BASE_BUNDLE_OVERRIDES_ASSET_NAME}.{locale} must be an object")
    text_fields = (
        "metadata_name",
        "metadata_description",
        "loop_name",
        "collaboration_summary",
        "spec_markdown",
        "workflow_collaboration_intent",
    )
    if not all(isinstance(fields.get(field), str) and fields[field].strip() for field in text_fields):
        raise ValueError(f"{LOCALIZED_BASE_BUNDLE_OVERRIDES_ASSET_NAME}.{locale} missing text fields")
    roles = fields.get("roles")
    if not isinstance(roles, dict) or not roles:
        raise ValueError(f"{LOCALIZED_BASE_BUNDLE_OVERRIDES_ASSET_NAME}.{locale}.roles must be an object")
    return {
        **{field: str(fields[field]).strip() for field in text_fields},
        "roles": {str(role_key): _localized_base_role_override_fields(locale, str(role_key), role) for role_key, role in roles.items()},
    }


def _localized_base_role_override_fields(locale: str, role_key: str, fields: Any) -> dict[str, str]:
    if not isinstance(fields, dict):
        raise ValueError(f"{LOCALIZED_BASE_BUNDLE_OVERRIDES_ASSET_NAME}.{locale}.roles.{role_key} must be an object")
    required_fields = ("name", "description", "prompt_markdown", "posture_notes")
    if not all(isinstance(fields.get(field), str) and fields[field].strip() for field in required_fields):
        raise ValueError(f"{LOCALIZED_BASE_BUNDLE_OVERRIDES_ASSET_NAME}.{locale}.roles.{role_key} missing text fields")
    return {field: str(fields[field]).strip() for field in required_fields}


def _apply_role_overrides(bundle: dict, role_overrides: dict[str, dict[str, str]]) -> None:
    for role in bundle.get("role_definitions", []):
        if not isinstance(role, dict):
            continue
        role_key = str(role.get("key") or "")
        overrides = role_overrides.get(role_key)
        if not overrides:
            continue
        role["name"] = overrides["name"]
        role["description"] = overrides["description"]
        role["prompt_markdown"] = overrides["prompt_markdown"]
        role["posture_notes"] = overrides["posture_notes"]


def _render_localized_base_bundle_overrides(overrides: dict[str, Any], context: dict[str, str]) -> None:
    safe_context = _SafeFormatContext(context)
    for field in (
        "metadata_name",
        "metadata_description",
        "loop_name",
        "collaboration_summary",
        "spec_markdown",
        "workflow_collaboration_intent",
    ):
        overrides[field] = Formatter().vformat(str(overrides[field]), (), safe_context)
    for role in overrides["roles"].values():
        for field in ("name", "description", "prompt_markdown", "posture_notes"):
            role[field] = Formatter().vformat(str(role[field]), (), safe_context)


class _SafeFormatContext(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
