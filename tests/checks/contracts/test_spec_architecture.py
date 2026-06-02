from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_spec_template_rendering_has_dedicated_boundary() -> None:
    specs_source = (REPO_ROOT / "src" / "loopora" / "specs.py").read_text(encoding="utf-8")
    markdown_source = (REPO_ROOT / "src" / "loopora" / "spec_markdown.py").read_text(encoding="utf-8")
    template_source = (REPO_ROOT / "src" / "loopora" / "spec_templates.py").read_text(encoding="utf-8")
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.spec_markdown import" in specs_source
    assert "from loopora.spec_templates import" in specs_source
    for marker in ("GENERIC_ROLE_NOTE_COPY", "ROLE_NOTE_DEFAULTS", "Delete this note whenever you want."):
        assert marker in template_source
        assert marker not in specs_source
        assert marker not in markdown_source
    assert "def compile_markdown_spec" not in specs_source
    assert "def compile_markdown_spec" in markdown_source
    assert "def compile_markdown_spec" not in template_source
    assert "spec_templates.py" in contracts_source
    assert "spec_markdown.py" in contracts_source
