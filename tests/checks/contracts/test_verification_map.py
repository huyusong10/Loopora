from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_verification_map_keeps_default_fast_gate_aligned_with_ci() -> None:
    text = (ROOT / "tests" / "README.md").read_text(encoding="utf-8")

    assert "Dependency compatibility, static JS syntax, Ruff, whitespace-safe diff, package build, and contract checks" in text
    assert "uv sync --locked --dry-run" in text
    assert "uv pip check" in text
    assert "find src/loopora/static -name '*.js' -print0 | xargs -0 -n1 node --check" in text
    assert "uv run ruff check src/loopora tests" in text
    assert "git diff --check" in text
    assert "uv build --out-dir tmp/package-check" in text
    assert "uv run pytest -q tests/checks/contracts" in text
    assert "uv run ruff check ." not in text
