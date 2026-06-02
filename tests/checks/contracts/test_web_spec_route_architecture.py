from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_web_spec_api_routes_have_dedicated_boundary() -> None:
    editor_source = (REPO_ROOT / "src" / "loopora" / "web_route_editor_api.py").read_text(encoding="utf-8")
    spec_source = (REPO_ROOT / "src" / "loopora" / "web_spec_api.py").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.web_spec_api import register_spec_api_routes" in editor_source
    assert "register_spec_api_routes(app, ctx)" in editor_source
    for marker in (
        "def _register_spec_validation_api_routes",
        "def _register_spec_document_api_routes",
        "def _register_markdown_prompt_api_routes",
        "def _register_spec_template_api_routes",
        "def _role_note_sections_from_strategy_source",
    ):
        assert marker in spec_source
        assert marker not in editor_source
    assert "web_spec_api.py" in design_source
