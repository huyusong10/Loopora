from __future__ import annotations

import re
import tomllib
from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient

from loopora.web import build_app


REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_ROOT = REPO_ROOT / "src" / "loopora" / "static"
STATIC_STYLE_PACKAGE_GLOB = "static/styles/*.css"
STATIC_STYLE_MANIFEST_PATTERN = "recursive-include src/loopora/static *.css *.js"
STATIC_STYLE_LAYERS = ("theme", "base", "layout", "components", "pages", "legacy")
LOGO_ASSETS = ("logo.svg", "logo-with-text-horizontal.svg", "logo-with-text-horizontal-light.svg")
RUNTIME_PACKAGE_ASSET_GROUPS = (
    (("templates/*.html", "templates/partials/*.html"), "recursive-include src/loopora/templates *.html"),
    (("static/*.css", "static/*.js", "static/pages/*.css", "static/pages/*.js", "static/styles/*.css"), STATIC_STYLE_MANIFEST_PATTERN),
    (("assets/logo/*.svg",), "recursive-include src/loopora/assets/logo *.svg"),
    (("assets/prompts/*.md",), "recursive-include src/loopora/assets/prompts *.md"),
    (("assets/spec_practices/*.md",), "recursive-include src/loopora/assets/spec_practices *.md"),
    (("assets/alignment/*.md", "assets/alignment/*.json", "assets/alignment/*.yml"), "recursive-include src/loopora/assets/alignment *.md *.json *.yml"),
    (("assets/system_prompts/**/*.md",), "recursive-include src/loopora/assets/system_prompts *.md"),
)


def test_global_stylesheets_are_template_linked_with_layer_versions() -> None:
    web_source = (REPO_ROOT / "src" / "loopora" / "web.py").read_text(encoding="utf-8")
    global_styles_template = (REPO_ROOT / "src" / "loopora" / "templates" / "_global_stylesheets.html").read_text(
        encoding="utf-8"
    )
    base_template = (REPO_ROOT / "src" / "loopora" / "templates" / "base.html").read_text(encoding="utf-8")
    auth_template = (REPO_ROOT / "src" / "loopora" / "templates" / "auth.html").read_text(encoding="utf-8")
    console_template = (REPO_ROOT / "src" / "loopora" / "templates" / "run_console.html").read_text(encoding="utf-8")
    index_template = (REPO_ROOT / "src" / "loopora" / "templates" / "index.html").read_text(encoding="utf-8")
    bundles_template = (REPO_ROOT / "src" / "loopora" / "templates" / "bundles.html").read_text(encoding="utf-8")
    app_css = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")
    legacy_css = (STATIC_ROOT / "styles" / "legacy.css").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "STATIC_STYLE_LAYERS = (" in web_source
    assert "def versioned_asset_url(" in web_source
    assert "def static_style_urls()" in web_source
    assert "def logo_asset_url(" in web_source
    assert "templates.env.globals[\"logo_asset_url\"] = logo_asset_url" in web_source
    assert "templates.env.globals[\"static_style_urls\"] = static_style_urls" in web_source
    for layer in STATIC_STYLE_LAYERS:
        assert f'"styles/{layer}.css"' in web_source
        assert (STATIC_ROOT / "styles" / f"{layer}.css").exists()
    for logo_asset in LOGO_ASSETS:
        assert f"logo_asset_url('{logo_asset}')" in base_template + auth_template + console_template + index_template + bundles_template
        assert (REPO_ROOT / "src" / "loopora" / "assets" / "logo" / logo_asset).exists()
    assert '"app.css"' in web_source
    assert "{% for stylesheet_href in static_style_urls() %}" in global_styles_template
    assert '<link rel="stylesheet" href="{{ stylesheet_href }}" />' in global_styles_template
    assert '{% include "_global_stylesheets.html" %}' in base_template
    assert '{% include "_global_stylesheets.html" %}' in auth_template
    assert '{% include "_global_stylesheets.html" %}' in console_template
    assert "@import url(" not in app_css
    assert 'content: url("/logo/' not in legacy_css
    assert 'src="/logo/' not in base_template + auth_template + console_template + index_template + bundles_template
    assert 'href="/logo/' not in base_template + auth_template + console_template
    assert "templates load theme/base/layout/components/pages/legacy/app styles directly" in design_source
    assert "Global Web brand assets use the same cache-busted template boundary as CSS" in design_source
    assert "Deep Visual Polish" in (STATIC_ROOT / "styles" / "legacy.css").read_text(encoding="utf-8")


def test_logo_assets_are_served(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service))

    response = client.get("/logo/logo.svg")
    assert response.status_code == HTTPStatus.OK
    assert "image/svg+xml" in response.headers["content-type"]


def test_network_mode_auth_page_uses_request_locale_and_shared_styles(service_factory) -> None:
    service = service_factory(scenario="success")
    client = TestClient(build_app(service=service, bind_host="0.0.0.0", auth_token="secret-token"))

    unauthorized = client.get("/", headers={"Accept-Language": "zh-CN;q=0.1,en-US;q=0.9"})

    assert unauthorized.status_code == HTTPStatus.UNAUTHORIZED
    assert re.search(r'<html\s+lang="en"\s+data-locale="en"\s+data-theme="light"\s*>', unauthorized.text)
    assert "loopora:theme" in unauthorized.text
    assert "loopora:locale" in unauthorized.text
    shared_style_hrefs = (
        "/static/styles/theme.css?v=",
        "/static/styles/base.css?v=",
        "/static/styles/layout.css?v=",
        "/static/styles/components.css?v=",
        "/static/styles/pages.css?v=",
        "/static/styles/legacy.css?v=",
        "/static/app.css?v=",
    )
    shared_style_positions = [unauthorized.text.index(href) for href in shared_style_hrefs]
    assert shared_style_positions == sorted(shared_style_positions)
    shared_logo_hrefs = (
        "/logo/logo.svg?v=",
        "/logo/logo-with-text-horizontal.svg?v=",
        "/logo/logo-with-text-horizontal-light.svg?v=",
    )
    assert all(href in unauthorized.text for href in shared_logo_hrefs)
    assert "<style>" not in unauthorized.text
    assert 'data-testid="auth-card"' in unauthorized.text
    assert 'data-testid="auth-copy-stack"' in unauthorized.text
    assert 'data-testid="auth-token-form"' in unauthorized.text
    assert 'data-testid="auth-token-input"' in unauthorized.text
    assert "Loopora · Auth token required" in unauthorized.text
    assert "Auth token required" in unauthorized.text
    assert "需要访问令牌" in unauthorized.text
    assert "X-Loopora-Token" in unauthorized.text
    assert "X-Other-Token" not in unauthorized.text
    assert "?token=&lt;your-token&gt;" not in unauthorized.text
    assert 'class="auth-logo" aria-hidden="true" data-testid="auth-logo"' in unauthorized.text
    assert "brand-lockup-image--light" in unauthorized.text
    assert "brand-lockup-image--dark" in unauthorized.text

    unauthenticated_css = client.get("/static/app.css")
    assert unauthenticated_css.status_code == HTTPStatus.OK
    assert "text/css" in unauthenticated_css.headers["content-type"]
    assert "@import url(" not in unauthenticated_css.text
    assert ".global-workdir-context {" in unauthenticated_css.text

    unauthenticated_legacy_css = client.get("/static/styles/legacy.css")
    assert unauthenticated_legacy_css.status_code == HTTPStatus.OK
    assert "text/css" in unauthenticated_legacy_css.headers["content-type"]
    assert ".auth-shell {" in unauthenticated_legacy_css.text

    unauthenticated_logo = client.get("/logo/logo.svg")
    assert unauthenticated_logo.status_code == HTTPStatus.OK
    assert "image/svg+xml" in unauthenticated_logo.headers["content-type"]
    assert all(
        selector in unauthenticated_legacy_css.text
        for selector in (
            ".auth-shell {",
            ".auth-card {",
            ".auth-form {",
            ".auth-token-row {",
            ".auth-copy-stack {",
            '[data-theme="dark"] .auth-card {',
            'html[data-theme="dark"] .brand-lockup-image--light {',
            'html[data-theme="dark"] .brand-lockup-image--dark {',
        )
    )


def test_global_web_shell_stays_readable_on_narrow_viewports() -> None:
    base_template = (REPO_ROOT / "src" / "loopora" / "templates" / "base.html").read_text(encoding="utf-8")
    support_template = (REPO_ROOT / "src" / "loopora" / "templates" / "support.html").read_text(encoding="utf-8")
    app_styles = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")
    legacy_styles = (STATIC_ROOT / "styles" / "legacy.css").read_text(encoding="utf-8")
    alignment_styles = (STATIC_ROOT / "pages" / "alignment.css").read_text(encoding="utf-8")
    workflow_styles = (STATIC_ROOT / "pages" / "workflow_editor.css").read_text(encoding="utf-8")
    run_detail_styles = (STATIC_ROOT / "pages" / "run_detail.css").read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert 'data-testid="top-nav"' in base_template
    assert 'data-testid="global-workdir-context"' in base_template
    assert 'data-testid="global-manual-copy"' in base_template
    assert 'class="input-with-action{% if access_state.native_dialogs_enabled %} support-target-control{% endif %}"' in support_template
    assert "Global Web shell responsiveness is a first-use access boundary" in design_source
    assert all(fragment in app_styles for fragment in (
        ".global-workdir-context span {\n  flex: 0 0 auto;",
        ".global-workdir-context code {\n  flex: 1 1 18rem;",
        "word-break: normal;",
        ".top-nav {\n    --top-nav-item-height: 44px;",
        ".top-nav-links {\n    flex-wrap: nowrap;\n    overflow-x: auto;",
        ".top-nav-link,\n  .top-nav-links .nav-dropdown,\n  .top-nav .nav-preferences-toggle {\n    flex: 0 0 auto;\n    width: auto;\n    min-width: max-content;",
        ".top-nav-link,\n  .top-nav .nav-preferences-toggle,\n  .display-preferences-toggle {\n    min-height: var(--top-nav-item-height);",
        ".display-preferences-toggle {\n    width: var(--top-nav-item-height);\n    min-width: var(--top-nav-item-height);",
        ".global-workdir-context {\n    display: grid;\n    grid-template-columns: minmax(0, 1fr);",
        ".primary-button,\n  .secondary-button,\n  .ghost-button,\n  button {\n    min-height: 44px;",
        ".help-dot,\n  .help-dot--tips {\n    width: 44px;\n    height: 44px;\n    min-width: 44px;\n    min-height: 44px;",
        ".manual-recovery-command-copy textarea {\n  width: 100%;\n  min-height: 5.5rem;",
        ".global-manual-copy textarea {\n  width: 100%;\n  min-height: 5.5rem;",
    ))
    assert all(fragment in legacy_styles for fragment in (
        "--top-nav-item-height: 44px;",
        ".top-nav-links {\n    gap: 6px;\n    flex-wrap: nowrap;\n    overflow-x: auto;",
        ".top-nav-links .nav-dropdown {\n    flex: 0 0 auto;\n    width: auto;",
        ".top-nav-link {\n    flex: 0 0 auto;\n    width: auto;\n    min-width: max-content;",
        ".top-nav .nav-preferences-toggle {\n    width: auto;\n    min-width: max-content;",
        ".display-preferences-toggle {\n    width: var(--top-nav-item-height);\n    min-width: var(--top-nav-item-height);\n    min-height: var(--top-nav-item-height);",
        ".support-target-control,\n  .input-with-multi-actions {\n    grid-template-columns: minmax(0, 1fr);",
        ".support-target-control > :is(.primary-button, .secondary-button, .ghost-button, button),",
        ".input-with-multi-actions > :is(.primary-button, .secondary-button, .ghost-button, button) {\n    width: 100%;",
        ".primary-button,\n  .secondary-button,\n  .ghost-button,\n  button {\n    min-height: 44px;",
        ".help-dot,\n  .help-dot--tips {\n    width: 44px;\n    height: 44px;\n    min-width: 44px;\n    min-height: 44px;",
    ))
    assert all(fragment in alignment_styles for fragment in (
        ".bundle-sidebar-action,\n.bundle-sidebar-nav a {\n  display: flex;\n  align-items: center;\n  gap: 10px;\n  min-height: 44px;",
        ".alignment-starter-disclosure > summary {\n  display: inline-flex;\n  align-items: center;\n  gap: 8px;\n  min-height: 44px;",
        ".alignment-tool-tabs button {\n  min-height: 44px;",
        ".alignment-tools-close {\n  flex: 0 0 auto;\n  width: 44px;\n  min-height: 44px;",
        ".alignment-agent-launch-copy-button {\n  width: 44px;\n  height: 44px;\n  min-height: 44px;",
        ".alignment-agent-launch-manual-copy textarea {\n  width: 100%;\n  min-height: 5.5rem;",
        ".alignment-preview-tab {\n  min-height: 44px;",
        ".bundle-sidebar-action {\n    min-height: 44px;",
    ))
    assert ".workflow-loop-pill {\n  display: inline-flex;\n  align-items: center;\n  gap: 8px;\n  min-height: 44px;" in workflow_styles
    assert ".trace-material-disclosure > summary {\n  display: flex;\n  align-items: center;\n  gap: 8px;\n  min-height: 44px;" in run_detail_styles


def test_global_web_feedback_replaces_blocking_alerts() -> None:
    base_template = (REPO_ROOT / "src" / "loopora" / "templates" / "base.html").read_text(encoding="utf-8")
    bundle_detail_template = (REPO_ROOT / "src" / "loopora" / "templates" / "bundle_detail.html").read_text(
        encoding="utf-8"
    )
    app_script = (REPO_ROOT / "src" / "loopora" / "static" / "app.js").read_text(encoding="utf-8")
    app_styles = (STATIC_ROOT / "app.css").read_text(encoding="utf-8") + (STATIC_ROOT / "styles" / "legacy.css").read_text(
        encoding="utf-8"
    )

    assert 'id="app-feedback"' in base_template
    assert 'data-testid="app-feedback"' in base_template
    assert 'role="status"' in base_template
    assert "function showAppFeedback(message" in app_script
    assert "showAppFeedback(error.message || pickText" in app_script
    assert "showAppFeedback(pickText({" in app_script
    assert "button.dataset.pathActionMode === \"copy\"" in app_script
    assert "Path copied." in app_script
    assert "window.alert(" not in app_script
    assert all(
        fragment in app_styles
        for fragment in (".app-feedback", ".app-feedback.is-error", ".delete-preview", ".status-validating", ".status-repairing")
    )
    assert all(
        fragment in app_script
        for fragment in (
            "function handleReturnedSurfaceUpdateFeedback()", "surface_updated",
            "function openHashLinkedDisclosure()", "function bindHashLinkedDisclosures()",
            "window.addEventListener(\"hashchange\", openHashLinkedDisclosure)", "target.closest(\"details\")",
            "validating: \"校验中\"", "repairing: \"自动修复\"", "function comparableWorkdir(value)",
            'path.startsWith("/private/tmp/")', "function sameWorkdir(left, right", "allowEmptyRight = true",
            "sameWorkdir,", "function tutorialFitPrefersDirectPath(payload)", "setupBlockers.includes(\"prefer_direct_path\")",
            "function tutorialFitSetupCommandState(payload", "setupGateBlockers", "setupGateReady",
            "routePreviewExecutable", "routePreviewBlockers", "function syncReturnToWorkdirContext(url, workdir",
            "function syncWorkdirFormAction(targetForm", "function syncWorkdirDatasetUrl(element",
            "function workdirContextModeForUrl(url", "function applyWorkdirContextToUrl(url", "context.hidden = !value",
            "document.querySelectorAll(\"[data-current-workdir]\")", "element.dataset.currentWorkdir = value",
            "loopora:workdirchange", "detail: {workdir: value}",
            "url.searchParams.delete(\"workdir\")", "function syncWorkdirContext(workdir", "NAVIGATION_CONTEXT_LINK_SELECTOR",
            "function navigationControlHref(control)", "function setNavigationControlHref(control, href)",
            "function navigationControlIsBlocked(control)", "data-direct-path-disabled-href", "setNavigationControlHref(link",
            "card.dataset.workdirContextOpenCard", "const isContextCard = Boolean(normalizeWorkdirContextMode(mode))",
            "syncWorkdirDatasetUrl(card, \"openCard\", value, mode, {", "preserveTargetContext: !isContextCard",
            "function activeAlignmentComposerReturnTarget(link",
            "allowBlocked: true", "document.querySelectorAll(NAVIGATION_CONTEXT_LINK_SELECTOR)",
            "function bindActiveAlignmentComposerReturnLinks()", "activeSavedAlignmentSessionForWorkdir(target.workdir)",
            "const navMenuItems = (root)", "const focusNavMenuItem = (root, index)",
            "focusNavMenuItem(root, currentIndex >= 0 ? currentIndex + 1 : 0)", "closeMenu(root, {restoreFocus: true})",
            "tooltip.id = \"help-floating-tooltip\"", "target.setAttribute(\"aria-describedby\", tooltip.id)",
            "button.addEventListener(\"keydown\", (event) =>", "document.body.dataset.boundHelpTooltipDismiss",
            "activeHelpTarget.contains(event.target)", 'sessionUrl.searchParams.set("alignment_session_id", session.id)',
            "tutorialFitPrefersDirectPath,", "tutorialFitSetupCommandState,", "syncWorkdirContext,", "syncWorkdirFormAction,",
        )
    )
    assert all(
        fragment in bundle_detail_template
        for fragment in (
            'data-testid="bundle-action-error" data-return-feedback-param="bundle_action_error" aria-live="polite"',
            'request.query_params.get("saved") == "1"',
            'class="field-status is-success" data-return-feedback-param="saved" aria-live="polite"',
            'data-surface-update-feedback data-return-feedback-param="surface_updated" aria-live="polite"',
            'data-return-feedback-param="created_from_loop"',
        )
    )


def test_app_css_style_layers_are_packaged_for_wheel_and_sdist() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["loopora"]
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert STATIC_STYLE_PACKAGE_GLOB in package_data
    assert STATIC_STYLE_MANIFEST_PATTERN in manifest


def test_runtime_package_assets_keep_wheel_and_sdist_manifests_aligned() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["loopora"]
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    for package_globs, manifest_pattern in RUNTIME_PACKAGE_ASSET_GROUPS:
        assert all(package_glob in package_data for package_glob in package_globs)
        assert manifest_pattern in manifest
