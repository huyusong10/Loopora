from __future__ import annotations

from pathlib import Path

from loopora.markdown_tools import looks_binary, render_safe_markdown_html
from loopora.service import LooporaError
from loopora.specs import (
    SpecError,
    compile_markdown_spec,
    resolve_spec_file_path,
    spec_file_read_error,
    spec_file_save_error,
)

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
    spec_path = resolve_spec_file_path(Path(path_text))
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


def _spec_document_read_error(exc: BaseException) -> str:
    return spec_file_read_error(exc)


def _spec_document_save_error(exc: BaseException) -> str:
    return spec_file_save_error(exc)


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
