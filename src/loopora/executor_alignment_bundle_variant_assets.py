from __future__ import annotations

from copy import deepcopy
from string import Formatter
from typing import Any


def apply_alignment_bundle_variant_fixture(bundle: dict, *, fixture: dict[str, Any]) -> None:
    metadata = bundle.get("metadata") if isinstance(bundle.get("metadata"), dict) else {}
    loop = bundle.get("loop") if isinstance(bundle.get("loop"), dict) else {}
    spec = bundle.get("spec") if isinstance(bundle.get("spec"), dict) else {}
    metadata["name"] = fixture["metadata_name"]
    metadata["description"] = fixture["metadata_description"]
    loop["name"] = fixture["loop_name"]
    bundle["metadata"] = metadata
    bundle["loop"] = loop
    bundle["collaboration_summary"] = fixture["collaboration_summary"]
    spec["markdown"] = fixture["spec_markdown"]
    bundle["spec"] = spec
    bundle["workflow"] = deepcopy(fixture["workflow"])


def alignment_bundle_variant_fixture(
    fixtures: dict[str, dict[str, Any]],
    *,
    fixture_key: str,
    asset_name: str,
    context: dict[str, str] | None = None,
) -> dict[str, Any]:
    fixture = fixtures.get(str(fixture_key or ""))
    if not isinstance(fixture, dict):
        raise ValueError(f"missing alignment bundle variant fixture in {asset_name}: {fixture_key}")
    rendered = deepcopy(fixture)
    if context:
        _render_alignment_bundle_variant_fixture(rendered, context)
    return rendered


def alignment_bundle_variant_fixtures_from_asset(asset: dict[str, Any], *, asset_name: str) -> dict[str, dict[str, Any]]:
    if asset.get("schema_version") != 1 or not isinstance(asset.get("fixtures"), dict):
        raise ValueError(f"{asset_name} must define schema_version 1 and fixtures")
    return {
        str(fixture_key): alignment_bundle_variant_fixture_fields(asset_name, str(fixture_key), fixture) for fixture_key, fixture in asset["fixtures"].items()
    }


def alignment_bundle_variant_fixture_fields(asset_name: str, fixture_key: str, fixture: Any) -> dict[str, Any]:
    if not isinstance(fixture, dict):
        raise ValueError(f"{asset_name}.{fixture_key} must be an object")
    text_fields = (
        "metadata_name",
        "metadata_description",
        "loop_name",
        "collaboration_summary",
        "spec_markdown",
    )
    if not all(isinstance(fixture.get(field), str) and fixture[field].strip() for field in text_fields):
        raise ValueError(f"{asset_name}.{fixture_key} missing text fields")
    workflow = fixture.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError(f"{asset_name}.{fixture_key}.workflow must be an object")
    _validate_alignment_bundle_variant_workflow(asset_name, fixture_key, workflow)
    return {
        **{field: str(fixture[field]).strip() for field in text_fields},
        "workflow": deepcopy(workflow),
    }


def _validate_alignment_bundle_variant_workflow(asset_name: str, fixture_key: str, workflow: dict[str, Any]) -> None:
    if workflow.get("version") != 1 or not isinstance(workflow.get("preset"), str) or not workflow["preset"].strip():
        raise ValueError(f"{asset_name}.{fixture_key}.workflow must define version 1 and preset")
    if not isinstance(workflow.get("collaboration_intent"), str) or not workflow["collaboration_intent"].strip():
        raise ValueError(f"{asset_name}.{fixture_key}.workflow missing collaboration_intent")
    role_ids = _validate_alignment_bundle_variant_roles(asset_name, fixture_key, workflow.get("roles"))
    _validate_alignment_bundle_variant_steps(asset_name, fixture_key, workflow.get("steps"), role_ids)


def _validate_alignment_bundle_variant_roles(asset_name: str, fixture_key: str, roles: Any) -> set[str]:
    if not isinstance(roles, list) or not roles:
        raise ValueError(f"{asset_name}.{fixture_key}.workflow.roles must be a non-empty list")
    role_ids = {_required_text(role, "id", asset_name=asset_name, fixture_key=fixture_key, collection="roles") for role in roles if isinstance(role, dict)}
    if len(role_ids) != len(roles):
        raise ValueError(f"{asset_name}.{fixture_key}.workflow.roles must have unique object ids")
    for role in roles:
        if not isinstance(role, dict):
            raise ValueError(f"{asset_name}.{fixture_key}.workflow.roles entries must be objects")
        _required_text(role, "role_definition_key", asset_name=asset_name, fixture_key=fixture_key, collection="roles")
    return role_ids


def _validate_alignment_bundle_variant_steps(asset_name: str, fixture_key: str, steps: Any, role_ids: set[str]) -> None:
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"{asset_name}.{fixture_key}.workflow.steps must be a non-empty list")
    step_ids = {_required_text(step, "id", asset_name=asset_name, fixture_key=fixture_key, collection="steps") for step in steps if isinstance(step, dict)}
    if len(step_ids) != len(steps):
        raise ValueError(f"{asset_name}.{fixture_key}.workflow.steps must have unique object ids")
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError(f"{asset_name}.{fixture_key}.workflow.steps entries must be objects")
        role_id = _required_text(step, "role_id", asset_name=asset_name, fixture_key=fixture_key, collection="steps")
        if role_id not in role_ids:
            raise ValueError(f"{asset_name}.{fixture_key}.workflow step references unknown role_id: {role_id}")


def _required_text(entry: dict[str, Any], key: str, *, asset_name: str, fixture_key: str, collection: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{asset_name}.{fixture_key}.workflow.{collection} missing {key}")
    return value.strip()


def _render_alignment_bundle_variant_fixture(fixture: dict[str, Any], context: dict[str, str]) -> None:
    safe_context = _SafeFormatContext(context)
    for field in ("metadata_name", "metadata_description", "loop_name", "collaboration_summary", "spec_markdown"):
        fixture[field] = Formatter().vformat(str(fixture[field]), (), safe_context)
    workflow = fixture.get("workflow")
    if isinstance(workflow, dict) and isinstance(workflow.get("collaboration_intent"), str):
        workflow["collaboration_intent"] = Formatter().vformat(workflow["collaboration_intent"], (), safe_context)


class _SafeFormatContext(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
