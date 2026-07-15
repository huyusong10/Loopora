from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from loopora.bundle_contract import BundleError
from loopora.bundle_normalization import normalize_bundle


def resolve_bundle_file_path(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise BundleError("bundle file could not be read") from exc


def read_bundle_file_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise BundleError("bundle file must be UTF-8 encoded YAML") from exc
    except FileNotFoundError as exc:
        raise BundleError("bundle file does not exist") from exc
    except (OSError, ValueError) as exc:
        raise BundleError("bundle file could not be read") from exc


def load_bundle_file(path: Path) -> dict[str, Any]:
    raw_text = read_bundle_file_text(path)
    return load_bundle_text(raw_text)


def load_bundle_text(raw_text: str) -> dict[str, Any]:
    return normalize_bundle(decode_bundle_text(raw_text))


def decode_bundle_text(raw_text: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:
        raise BundleError(_invalid_bundle_yaml_message(raw_text)) from exc
    if not isinstance(payload, Mapping):
        raise BundleError("bundle YAML must decode to an object")
    return dict(payload)


def _invalid_bundle_yaml_message(raw_text: str) -> str:
    if any(_is_yaml_control_character(char) for char in raw_text):
        return "invalid bundle YAML: remove unsupported control characters"
    return "invalid bundle YAML: check Plan File YAML syntax"


def _is_yaml_control_character(char: str) -> bool:
    codepoint = ord(char)
    return codepoint < 32 and char not in {"\t", "\n", "\r"}


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
