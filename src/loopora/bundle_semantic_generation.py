from __future__ import annotations

import re
from collections.abc import Mapping

import yaml


def lint_alignment_bundle_generation_text(raw_text: str) -> list[str]:
    """Return raw-text issues for Web compiler generated bundle candidates."""

    issues: list[str] = []
    stripped = str(raw_text or "").strip()
    if not stripped:
        return issues
    non_empty_lines = [line.strip() for line in str(raw_text or "").splitlines() if line.strip()]
    if non_empty_lines and re.match(r"^```(?:yaml|yml)?\s*$", non_empty_lines[0], re.IGNORECASE):
        issues.append("Web alignment generated bundle_yaml must be one raw YAML document, not markdown-fenced output")
    if non_empty_lines and not re.match(r"^version\s*:\s*1(?:\s*(?:#.*)?)?$", non_empty_lines[0]):
        issues.append("Web alignment generated bundle_yaml must start with version: 1")
    issues.extend(lint_alignment_bundle_generation_metadata(raw_text))
    return issues


def lint_alignment_bundle_generation_metadata(raw_text: str) -> list[str]:
    """Return raw-YAML metadata issues for Web compiler generated bundle candidates."""

    try:
        payload = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError:
        return []
    if not isinstance(payload, Mapping):
        return []
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        return []
    metadata_keys = {str(key).strip() for key in metadata}
    if "source_bundle_id" not in metadata_keys and "revision" not in metadata_keys:
        return []
    return [
        "Web alignment generated bundles must omit metadata.source_bundle_id and metadata.revision; "
        "source context is temporary and final bundles are standalone candidates"
    ]
