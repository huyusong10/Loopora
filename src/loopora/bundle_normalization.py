from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.bundle_contract import (
    BUNDLE_VERSION,
    BundleError,
    normalize_bundle_identifier,
    normalize_bundle_integer,
)
from loopora.bundle_loop_settings import bundle_loop_role_execution_defaults, normalize_bundle_loop
from loopora.bundle_role_definitions import normalize_bundle_role_definitions
from loopora.bundle_workflow_normalization import normalize_bundle_workflow, validate_bundle_runtime_contract
from loopora.specs import SpecError, compile_markdown_spec


def normalize_bundle(payload: Mapping[str, object] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise BundleError("bundle payload must decode to an object")
    raw = dict(payload)
    version = _normalize_bundle_version(raw.get("version"))
    if version != BUNDLE_VERSION:
        raise BundleError(f"unsupported bundle version: {version}")

    metadata = _normalize_bundle_metadata(raw.get("metadata"))
    collaboration_summary = str(raw.get("collaboration_summary", "") or "").strip()
    if not collaboration_summary:
        raise BundleError("bundle collaboration_summary is required")
    loop = normalize_bundle_loop(raw.get("loop"))
    spec = _normalize_bundle_spec(raw.get("spec"))
    role_definitions = normalize_bundle_role_definitions(
        raw.get("role_definitions"),
        default_execution=bundle_loop_role_execution_defaults(loop),
    )
    workflow = normalize_bundle_workflow(raw.get("workflow"), role_definitions=role_definitions)
    validate_bundle_runtime_contract(loop=loop, role_definitions=role_definitions, workflow=workflow)
    return {
        "version": version,
        "metadata": metadata,
        "collaboration_summary": collaboration_summary,
        "loop": loop,
        "spec": spec,
        "role_definitions": role_definitions,
        "workflow": workflow,
    }


def _normalize_bundle_metadata(raw_metadata: object) -> dict[str, Any]:
    if raw_metadata is None:
        metadata = {}
    elif isinstance(raw_metadata, Mapping):
        metadata = dict(raw_metadata)
    else:
        raise BundleError("bundle metadata must be an object")
    name = str(metadata.get("name", "") or "").strip()
    if not name:
        raise BundleError("bundle metadata.name is required")
    revision = _normalize_bundle_revision(metadata)
    if revision < 1:
        raise BundleError("bundle metadata.revision must be >= 1")
    return {
        "bundle_id": normalize_bundle_identifier(metadata.get("bundle_id"), field_name="bundle metadata.bundle_id", allow_empty=True),
        "name": name,
        "description": str(metadata.get("description", "") or "").strip(),
        "source_bundle_id": normalize_bundle_identifier(
            metadata.get("source_bundle_id"),
            field_name="bundle metadata.source_bundle_id",
            allow_empty=True,
        ),
        "revision": revision,
    }


def _normalize_bundle_version(value: object) -> int:
    return normalize_bundle_integer(value, default=BUNDLE_VERSION, field_name="bundle version")


def _normalize_bundle_revision(metadata: Mapping[str, Any]) -> int:
    if "revision" not in metadata:
        return 1
    value = metadata.get("revision")
    if value is None or (isinstance(value, str) and not value.strip()):
        raise BundleError("bundle metadata.revision must be an integer")
    return normalize_bundle_integer(value, default=1, field_name="bundle metadata.revision")


def _normalize_bundle_spec(raw_spec: object) -> dict[str, str]:
    if not isinstance(raw_spec, Mapping):
        raise BundleError("bundle spec must be an object")
    markdown = str(dict(raw_spec).get("markdown", "") or "").strip()
    if not markdown:
        raise BundleError("bundle spec.markdown is required")
    try:
        compile_markdown_spec(markdown)
    except SpecError as exc:
        raise BundleError(str(exc)) from exc
    return {"markdown": markdown}
