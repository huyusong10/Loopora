from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256

from loopora.token_security import scoped_token_matches, sign_scoped_token
from loopora.web_common_inputs import _coerce_bool


BUNDLE_IMPORT_PREVIEW_REVIEW_SCOPE = "bundle-import-preview-review-v1"

DEFAULT_BUNDLE_IMPORT_FORM = {
    "bundle_path": "",
    "bundle_yaml": "",
    "replace_bundle_id": "",
    "import_intent": "import",
    "start_immediately": False,
    "bundle_preview_reviewed": "",
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
    normalized["start_immediately"] = _coerce_bool(normalized.get("start_immediately", False))
    normalized["bundle_preview_reviewed"] = str(normalized.get("bundle_preview_reviewed", "") or "")
    return normalized


def _normalize_bundle_derive_form(values: Mapping[str, object] | None) -> dict[str, object]:
    normalized = dict(DEFAULT_BUNDLE_DERIVE_FORM)
    if not values:
        return normalized
    for key in normalized:
        if key in values:
            normalized[key] = values[key]
    return normalized


def bundle_import_preview_review_token(values: Mapping[str, object]) -> str:
    return sign_scoped_token(
        BUNDLE_IMPORT_PREVIEW_REVIEW_SCOPE,
        bundle_import_preview_source_digest(values),
    )


def bundle_import_preview_reviewed(values: Mapping[str, object], token: object) -> bool:
    return scoped_token_matches(
        str(token or ""),
        scope=BUNDLE_IMPORT_PREVIEW_REVIEW_SCOPE,
        value=bundle_import_preview_source_digest(values),
    )


def bundle_import_preview_source_digest(values: Mapping[str, object]) -> str:
    bundle_yaml = str(values.get("bundle_yaml", ""))
    bundle_path = str(values.get("bundle_path", "")).strip()
    source_kind = "yaml" if bundle_yaml.strip() else "path"
    source_value = bundle_yaml if source_kind == "yaml" else bundle_path
    content = f"{source_kind}\0{source_value}".encode()
    return sha256(content).hexdigest()
