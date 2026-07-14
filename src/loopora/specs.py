from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Any
from uuid import uuid4

from loopora.spec_markdown import (
    SpecError as SpecError,
    compile_markdown_spec as compile_markdown_spec,
    resolve_role_note as resolve_role_note,
)
from loopora.spec_templates import (
    render_spec_template as _render_spec_template,
    render_spec_template_for_strategy_source as _render_spec_template_for_strategy_source,
)

SPEC_FILE_EXISTS_ERROR = "spec file already exists"
SPEC_FILE_DIRECTORY_ERROR = "spec path must be a Markdown file, not a directory"
SPEC_FILE_INIT_ERROR = "spec file could not be initialized"
SPEC_FILE_READ_ERROR = "spec file could not be read"
SPEC_FILE_SAVE_ERROR = "spec file could not be saved"


def resolve_spec_file_path(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise OSError("spec path could not be resolved") from exc


def spec_template(locale: str = "zh", workflow: dict[str, Any] | None = None) -> str:
    return render_spec_template(locale=locale, workflow=workflow)


def render_spec_template(
    locale: str = "zh",
    workflow: dict[str, Any] | None = None,
    *,
    strategy_source: dict[str, Any] | None = None,
) -> str:
    return _render_spec_template(
        locale=locale,
        workflow=workflow,
        strategy_source=strategy_source,
    )


def render_spec_template_for_strategy_source(
    locale: str = "zh",
    strategy_source: dict[str, Any] | None = None,
) -> str:
    return _render_spec_template_for_strategy_source(locale=locale, strategy_source=strategy_source)


def init_spec_file(path: Path, *, locale: str = "zh") -> Path:
    return init_spec_file_for_strategy_source(path, locale=locale, strategy_source=None)


def init_spec_file_for_workflow(path: Path, *, locale: str = "zh", workflow: dict[str, Any] | None = None) -> Path:
    return init_spec_file_for_strategy_source(path, locale=locale, strategy_source=workflow)


def init_spec_file_for_strategy_source(
    path: Path,
    *,
    locale: str = "zh",
    strategy_source: dict[str, Any] | None = None,
) -> Path:
    resolved_path = resolve_spec_file_path(path)
    if resolved_path.exists():
        if resolved_path.is_dir():
            raise IsADirectoryError(SPEC_FILE_DIRECTORY_ERROR)
        raise FileExistsError(SPEC_FILE_EXISTS_ERROR)
    save_spec_file(
        resolved_path,
        render_spec_template_for_strategy_source(locale=locale, strategy_source=strategy_source),
        create_parent=True,
    )
    return resolved_path


def save_spec_file(path: Path, markdown_text: str, *, create_parent: bool = True) -> Path:
    resolved_path = resolve_spec_file_path(path)
    if resolved_path.exists() and resolved_path.is_dir():
        raise IsADirectoryError(SPEC_FILE_DIRECTORY_ERROR)
    if create_parent:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(resolved_path, markdown_text)
    return resolved_path


def _atomic_write_text(path: Path, content: str) -> None:
    tmp = path.with_name(f".{path.name}.tmp.{uuid4().hex}")
    try:
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        with suppress(OSError):
            tmp.unlink()
        raise


def read_and_compile(path: Path) -> tuple[str, dict]:
    markdown_text = load_spec_file(path)
    return markdown_text, compile_markdown_spec(markdown_text)


def load_spec_file(path: Path) -> str:
    resolved_path = resolve_spec_file_path(path)
    try:
        return resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SpecError("spec file must be UTF-8 encoded Markdown") from exc


def spec_file_init_error(exc: BaseException) -> str:
    if isinstance(exc, IsADirectoryError):
        return SPEC_FILE_DIRECTORY_ERROR
    if isinstance(exc, FileExistsError):
        return SPEC_FILE_EXISTS_ERROR
    if isinstance(exc, OSError):
        return SPEC_FILE_INIT_ERROR
    return str(exc)


def spec_file_read_error(exc: BaseException) -> str:
    if isinstance(exc, FileNotFoundError):
        return "spec file does not exist"
    if isinstance(exc, IsADirectoryError):
        return SPEC_FILE_DIRECTORY_ERROR
    if isinstance(exc, OSError):
        return SPEC_FILE_READ_ERROR
    return str(exc)


def spec_file_save_error(exc: BaseException) -> str:
    if isinstance(exc, IsADirectoryError):
        return SPEC_FILE_DIRECTORY_ERROR
    if isinstance(exc, OSError):
        return SPEC_FILE_SAVE_ERROR
    return str(exc)
