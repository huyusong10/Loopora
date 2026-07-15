from __future__ import annotations

from pathlib import Path
from typing import Any

from loopora.spec_markdown import (
    SpecError as SpecError,
    compile_markdown_spec as compile_markdown_spec,
    resolve_role_note as resolve_role_note,
)
from loopora.spec_templates import (
    render_spec_template as _render_spec_template,
    render_spec_template_for_strategy_source as _render_spec_template_for_strategy_source,
)


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
    if path.exists():
        raise FileExistsError(f"spec already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_spec_template_for_strategy_source(locale=locale, strategy_source=strategy_source),
        encoding="utf-8",
    )
    return path


def read_and_compile(path: Path) -> tuple[str, dict]:
    markdown_text = load_spec_file(path)
    return markdown_text, compile_markdown_spec(markdown_text)


def load_spec_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SpecError("spec file must be UTF-8 encoded Markdown") from exc
