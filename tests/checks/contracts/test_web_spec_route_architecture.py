from __future__ import annotations

from pathlib import Path

from strategy_source_architecture_test_support import design_boundary_source


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_web_spec_api_routes_have_dedicated_boundary() -> None:
    editor_source = (REPO_ROOT / "src" / "loopora" / "web_route_editor_api.py").read_text(encoding="utf-8")
    spec_source = (REPO_ROOT / "src" / "loopora" / "web_spec_api.py").read_text(encoding="utf-8")
    document_source = (REPO_ROOT / "src" / "loopora" / "web_spec_document_api_routes.py").read_text(encoding="utf-8")
    prompt_source = (REPO_ROOT / "src" / "loopora" / "web_markdown_prompt_api_routes.py").read_text(encoding="utf-8")
    template_source = (REPO_ROOT / "src" / "loopora" / "web_spec_template_api_routes.py").read_text(encoding="utf-8")
    recovery_source = (REPO_ROOT / "src" / "loopora" / "web_spec_output_recovery.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.web_spec_api import register_spec_api_routes" in editor_source
    assert "register_spec_api_routes(app, ctx)" in editor_source
    assert "from loopora.web_spec_document_api_routes import register_spec_document_api_routes" in spec_source
    assert "from loopora.web_markdown_prompt_api_routes import register_markdown_prompt_api_routes" in spec_source
    assert "from loopora.web_spec_template_api_routes import register_spec_template_api_routes" in spec_source
    assert "register_spec_document_api_routes(app, ctx)" in spec_source
    assert "register_markdown_prompt_api_routes(app, ctx)" in spec_source
    assert "register_spec_template_api_routes(app, ctx)" in spec_source
    assert "def _register_spec_validation_api_routes" in document_source
    assert "def _register_spec_document_read_api_routes" in document_source
    assert "def _register_spec_save_api_route" in document_source
    assert "def register_markdown_prompt_api_routes" in prompt_source
    assert "def register_spec_template_api_routes" in template_source
    assert "def _role_note_sections_from_strategy_source" in template_source
    assert "def web_spec_output_recovery_payload" in recovery_source
    for marker in (
        "def _register_spec_validation_api_routes",
        "def _register_spec_document_read_api_routes",
        "def register_markdown_prompt_api_routes",
        "def register_spec_template_api_routes",
        "def _role_note_sections_from_strategy_source",
        "def web_spec_output_recovery_payload",
    ):
        assert marker not in editor_source
        assert marker not in spec_source
    assert "web_spec_api.py" in design_source
    assert "web_spec_document_api_routes.py" in design_source
    assert "web_markdown_prompt_api_routes.py" in design_source
    assert "web_spec_template_api_routes.py" in design_source
    assert "web_spec_output_recovery.py" in design_source


def test_web_bundle_api_routes_have_dedicated_boundary() -> None:
    editor_source = (REPO_ROOT / "src" / "loopora" / "web_route_editor_api.py").read_text(encoding="utf-8")
    bundle_source = (REPO_ROOT / "src" / "loopora" / "web_bundle_api_routes.py").read_text(encoding="utf-8")
    support_source = (REPO_ROOT / "src" / "loopora" / "web_editor_api_support.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.web_bundle_api_routes import register_bundle_api_routes" in editor_source
    assert "register_bundle_api_routes(app, ctx)" in editor_source
    for marker in (
        "def _register_bundle_record_api_routes",
        "def _register_bundle_import_api_routes",
        "def _register_bundle_export_api_routes",
        "web_bundle_import_file_workdir_recovery",
        "web_bundle_export_generation_recovery_payload",
        '"/api/bundles/import"',
        '"/api/bundles/{bundle_id}/delete-preview"',
    ):
        assert marker in bundle_source
        assert marker not in editor_source
    assert "api_asset_mutation_error_response" in support_source
    assert "api_asset_redirect_url" in support_source
    assert "web_bundle_api_routes.py" in design_source
    assert "web_editor_api_support.py" in design_source


def test_web_asset_catalog_api_routes_have_dedicated_boundary() -> None:
    editor_source = (REPO_ROOT / "src" / "loopora" / "web_route_editor_api.py").read_text(encoding="utf-8")
    asset_catalog_source = (REPO_ROOT / "src" / "loopora" / "web_asset_catalog_api_routes.py").read_text(encoding="utf-8")
    design_source = design_boundary_source()

    assert "from loopora.web_asset_catalog_api_routes import register_asset_catalog_api_routes" in editor_source
    assert "register_asset_catalog_api_routes(app, ctx)" in editor_source
    for marker in (
        "def _register_orchestration_api_routes",
        "def _register_role_definition_api_routes",
        "_orchestration_payload_from_mapping",
        "_role_definition_payload_from_mapping",
        '"/api/orchestrations/{orchestration_id}/delete-preview"',
        '"/api/role-definitions/{role_definition_id}/delete-preview"',
    ):
        assert marker in asset_catalog_source
        assert marker not in editor_source
    assert "web_asset_catalog_api_routes.py" in design_source
