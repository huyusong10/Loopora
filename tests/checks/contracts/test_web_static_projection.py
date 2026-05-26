from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_ROOT = REPO_ROOT / "src" / "loopora" / "static"


def test_app_css_is_layer_manifest_with_legacy_backstop() -> None:
    app_css = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")

    for layer in ("theme", "base", "layout", "components", "pages", "legacy"):
        assert f'@import url("./styles/{layer}.css");' in app_css
        assert (STATIC_ROOT / "styles" / f"{layer}.css").exists()
    assert "Deep Visual Polish" in (STATIC_ROOT / "styles" / "legacy.css").read_text(encoding="utf-8")


def test_run_detail_page_loads_projection_renderer_before_api_and_controller() -> None:
    scripts = (REPO_ROOT / "src" / "loopora" / "templates" / "partials" / "run_detail_scripts.html").read_text(encoding="utf-8")

    assert "initialProjection" in scripts
    assert scripts.index("pages/run_detail_projection.js") < scripts.index("pages/run_detail_api.js")
    assert scripts.index("pages/run_detail_projection.js") < scripts.index("pages/run_detail.js")


def test_run_detail_client_normalizes_run_payloads_through_web_projection() -> None:
    api_js = (STATIC_ROOT / "pages" / "run_detail_api.js").read_text(encoding="utf-8")
    page_js = (STATIC_ROOT / "pages" / "run_detail.js").read_text(encoding="utf-8")
    projection_js = (STATIC_ROOT / "pages" / "run_detail_projection.js").read_text(encoding="utf-8")

    assert "normalizeRunPayload(payload)" in api_js
    assert "normalizeInitialRun(runDetailData)" in page_js
    assert "web_projection" in projection_js
    assert "summary.run_status" in projection_js
