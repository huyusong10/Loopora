from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = ROOT / "src" / "loopora"


def test_loopora_source_does_not_use_wildcard_imports() -> None:
    offenders: list[str] = []
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders.extend(
            f"{path.relative_to(ROOT)}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names)
        )

    assert offenders == []


def test_repository_ignores_common_local_tool_outputs() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    for term in (
        "__pycache__/",
        "*.py[cod]",
        ".venv/",
        ".pytest_cache/",
        ".ruff_cache/",
        ".mypy_cache/",
        ".tox/",
        ".nox/",
        ".coverage",
        ".coverage.*",
        "htmlcov/",
        "coverage.xml",
        "junit*.xml",
        "test-results/",
        "playwright-report/",
        ".loopora/",
        ".log/",
        "*.log",
        "*.prof",
        "artifacts/real_search_loop_e2e/",
        "/tmp/",
        ".DS_Store",
        "*.egg",
        "*.egg-info/",
        "build/",
        "dist/",
        "/spec.md",
        ".agents/",
        ".claude/",
        ".codex/",
        ".opencode/",
    ):
        assert term in gitignore


def test_repository_text_normalization_is_declared_for_contributors() -> None:
    editorconfig = (ROOT / ".editorconfig").read_text(encoding="utf-8")
    gitattributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

    for term in (
        "root = true",
        "charset = utf-8",
        "end_of_line = lf",
        "insert_final_newline = true",
        "trim_trailing_whitespace = true",
        "indent_style = space",
        "[*.py]",
        "indent_size = 4",
        "[*.md]",
        "trim_trailing_whitespace = false",
    ):
        assert term in editorconfig

    for term in (
        "* text=auto eol=lf",
        "*.svg text eol=lf",
        "*.png binary",
        "*.pdf binary",
        "*.sqlite binary",
    ):
        assert term in gitattributes
