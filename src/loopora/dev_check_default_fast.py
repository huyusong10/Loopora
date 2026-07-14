from __future__ import annotations

"""Default-fast verification command catalog."""

DEFAULT_FAST_COMMANDS = (
    ("dependency_sync", "Check locked dependency resolution", "uv sync --locked --dry-run", ("uv", "sync", "--locked", "--dry-run")),
    ("dependency_compatibility", "Check dependency compatibility", "uv pip check", ("uv", "pip", "check")),
    (
        "static_js_syntax",
        "Check static JavaScript syntax",
        "find src/loopora/static -name '*.js' -print0 | xargs -0 -n1 node --check",
        None,
    ),
    ("python_static_checks", "Run Python static checks", "uv run ruff check src/loopora tests", ("uv", "run", "ruff", "check", "src/loopora", "tests")),
    ("whitespace_safe_diff", "Check whitespace-safe diff", "git diff --check", ("git", "diff", "--check")),
    ("package_build", "Build package", "uv build --out-dir tmp/package-check", ("uv", "build", "--out-dir", "tmp/package-check")),
    ("contract_checks", "Run contract checks", "uv run pytest -q tests/checks/contracts", ("uv", "run", "pytest", "-q", "tests/checks/contracts")),
)

__all__ = ("DEFAULT_FAST_COMMANDS",)
