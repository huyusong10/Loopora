from __future__ import annotations

from loopora.web_common_inputs import _coerce_bool
from loopora.web_loop_inputs import (
    DEFAULT_LOOP_FORM,
    _loop_form_is_pristine,
    _loop_payload_from_mapping,
    _normalize_loop_form,
)
from loopora.web_request_context import (
    _build_access_state,
    _extract_request_token,
    _is_loopback_host,
    _preferred_locale_from_accept_language,
    _preferred_request_locale,
)
from loopora.web_role_inputs import (
    DEFAULT_ROLE_DEFINITION_FORM,
    _archetype_options,
    _builtin_role_templates,
    _decorate_role_definition_overview,
    _normalize_role_definition_form,
    _role_definition_form_values_from_record,
    _role_definition_payload_from_mapping,
)
from loopora.web_strategy_inputs import (
    DEFAULT_ORCHESTRATION_FORM,
    _normalize_orchestration_form,
    _orchestration_form_values_from_record,
    _orchestration_payload_from_mapping,
    _strategy_source_for_spec_template,
)

from collections.abc import Mapping


from pathlib import Path

from loopora.markdown_tools import looks_binary, render_safe_markdown_html

from loopora.service import LooporaError

from loopora.specs import SpecError, compile_markdown_spec

SPEC_MARKDOWN_SUFFIXES = {".md", ".markdown"}

SPEC_DOCUMENT_MAX_BYTES = 1_000_000

def _load_spec_markdown_document(path_text: str, *, binary_error: str) -> tuple[Path, str]:
    spec_path = _resolve_spec_markdown_path(path_text)
    raw_bytes = spec_path.read_bytes()
    _assert_spec_markdown_content(raw_bytes, binary_error=binary_error)
    try:
        markdown_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LooporaError("spec file must be UTF-8 encoded Markdown") from exc
    return spec_path, markdown_text

def _resolve_spec_markdown_path(path_text: str) -> Path:
    spec_path = Path(path_text).expanduser().resolve()
    if spec_path.suffix.lower() not in SPEC_MARKDOWN_SUFFIXES:
        raise LooporaError("spec path must point to a Markdown file (.md or .markdown)")
    return spec_path

def _assert_spec_markdown_content(raw_bytes: bytes, *, binary_error: str) -> None:
    _assert_spec_markdown_size(raw_bytes)
    if looks_binary(raw_bytes):
        raise LooporaError(binary_error)

def _assert_spec_markdown_size(raw_bytes: bytes) -> None:
    if len(raw_bytes) > SPEC_DOCUMENT_MAX_BYTES:
        raise LooporaError(f"spec file is too large; maximum size is {SPEC_DOCUMENT_MAX_BYTES} bytes")

def _spec_validation_from_markdown(markdown_text: str) -> dict[str, object]:
    try:
        compiled = compile_markdown_spec(markdown_text)
    except SpecError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "check_count": 0,
            "check_mode": "",
        }
    return {
        "ok": True,
        "error": "",
        "check_count": len(compiled["checks"]),
        "check_mode": compiled["check_mode"],
    }

def _spec_document_payload(spec_path: Path, markdown_text: str) -> dict[str, object]:
    return {
        "ok": True,
        "path": str(spec_path.resolve()),
        "content": markdown_text,
        "rendered_html": render_safe_markdown_html(markdown_text),
        "validation": _spec_validation_from_markdown(markdown_text),
    }

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

__all__ = [
    "DEFAULT_BUNDLE_DERIVE_FORM",
    "DEFAULT_BUNDLE_IMPORT_FORM",
    "DEFAULT_LOOP_FORM",
    "DEFAULT_ORCHESTRATION_FORM",
    "DEFAULT_ROLE_DEFINITION_FORM",
    "_archetype_options",
    "_build_access_state",
    "_builtin_role_templates",
    "_coerce_bool",
    "_decorate_role_definition_overview",
    "_extract_request_token",
    "_is_loopback_host",
    "_loop_form_is_pristine",
    "_loop_payload_from_mapping",
    "_normalize_bundle_derive_form",
    "_normalize_bundle_import_form",
    "_normalize_loop_form",
    "_normalize_orchestration_form",
    "_normalize_role_definition_form",
    "_orchestration_form_values_from_record",
    "_orchestration_payload_from_mapping",
    "_preferred_locale_from_accept_language",
    "_preferred_request_locale",
    "_role_definition_form_values_from_record",
    "_role_definition_payload_from_mapping",
    "_spec_document_payload",
    "_strategy_source_for_spec_template",
]
