from __future__ import annotations

from collections.abc import Mapping

from loopora.web_common_inputs import _coerce_bool

DEFAULT_BUNDLE_IMPORT_FORM = {
    "bundle_path": "",
    "bundle_yaml": "",
    "replace_bundle_id": "",
    "start_immediately": True,
}

DEFAULT_BUNDLE_DERIVE_FORM = {
    "loop_id": "",
    "name": "",
    "description": "",
    "collaboration_summary": "",
}


def _normalize_bundle_import_form(values: Mapping[str, object] | None) -> dict[str, object]:
    normalized = dict(DEFAULT_BUNDLE_IMPORT_FORM)
    if not values:
        return normalized
    for key in normalized:
        if key in values:
            normalized[key] = values[key]
    normalized["start_immediately"] = _coerce_bool(normalized.get("start_immediately", True))
    return normalized


def _normalize_bundle_derive_form(values: Mapping[str, object] | None) -> dict[str, object]:
    normalized = dict(DEFAULT_BUNDLE_DERIVE_FORM)
    if not values:
        return normalized
    for key in normalized:
        if key in values:
            normalized[key] = values[key]
    return normalized
