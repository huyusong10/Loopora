from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from loopora.bundle_contract import BundleError
from loopora.bundle_normalization import normalize_bundle


def read_bundle_file_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise BundleError("bundle file must be UTF-8 encoded YAML") from exc


def load_bundle_file(path: Path) -> dict[str, Any]:
    raw_text = read_bundle_file_text(path)
    return load_bundle_text(raw_text)


def load_bundle_text(raw_text: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        raise BundleError(f"invalid bundle YAML: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise BundleError("bundle YAML must decode to an object")
    return normalize_bundle(payload)


def bundle_to_yaml(bundle: Mapping[str, object]) -> str:
    normalized = normalize_bundle(bundle)
    export_payload = json.loads(json.dumps(normalized, ensure_ascii=False))
    metadata = export_payload.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("source_bundle_id", None)
        metadata.pop("revision", None)
    return yaml.safe_dump(
        export_payload,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
