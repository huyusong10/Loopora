from __future__ import annotations

import tomllib

from web_static_projection_support import REPO_ROOT, STATIC_ROOT


STATIC_STYLE_PACKAGE_GLOB = "static/styles/*.css"
STATIC_STYLE_MANIFEST_PATTERN = "recursive-include src/loopora/static/styles *.css"


def test_app_css_is_layer_manifest_with_legacy_backstop() -> None:
    app_css = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")

    for layer in ("theme", "base", "layout", "components", "pages", "legacy"):
        assert f'@import url("./styles/{layer}.css");' in app_css
        assert (STATIC_ROOT / "styles" / f"{layer}.css").exists()
    assert "Deep Visual Polish" in (STATIC_ROOT / "styles" / "legacy.css").read_text(encoding="utf-8")


def test_app_css_style_layers_are_packaged_for_wheel_and_sdist() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["loopora"]
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert STATIC_STYLE_PACKAGE_GLOB in package_data
    assert STATIC_STYLE_MANIFEST_PATTERN in manifest
