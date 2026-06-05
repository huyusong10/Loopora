from __future__ import annotations

from pathlib import Path

from review_runner_test_support import write_source_lines, write_term_hints_report


def test_review_term_hints_scan_visible_text_not_template_identifiers(monkeypatch, tmp_path: Path) -> None:
    write_source_lines(
        tmp_path,
        "src/loopora/templates/page.html",
        [
            '<a href="/loops/new/bundle" data-testid="bundle-import-link">Import plan</a>',
            '<h2><span data-lang="en">Import Existing Bundle / YAML</span></h2>',
            '<button aria-label="{{ \'Open bundle chooser\' if page_locale == \'en\' else \'打开方案选择器\' }}"></button>',
        ],
    )

    report = write_term_hints_report(
        monkeypatch,
        tmp_path,
        globs=["src/loopora/templates/*.html"],
        terms=["bundle", "YAML"],
    )

    assert "page.html:1" not in report
    assert "`src/loopora/templates/page.html:2` `bundle`" in report
    assert "`src/loopora/templates/page.html:2` `YAML`" in report
    assert "`src/loopora/templates/page.html:3` `bundle`" in report
    assert "data-testid" not in report
    assert "href=" not in report


def test_review_term_hints_ignore_markdown_link_and_html_attribute_urls(monkeypatch, tmp_path: Path) -> None:
    write_source_lines(
        tmp_path,
        "README.md",
        [
            '<a href="https://example.test/actions/workflows/ci.yml">',
            '  <img alt="CI" src="https://example.test/actions/workflows/ci.yml/badge.svg">',
            "</a>",
            "[CI badge](https://example.test/actions/workflows/ci.yml)",
            "Workflow controls belong on expert pages.",
        ],
    )

    report = write_term_hints_report(
        monkeypatch,
        tmp_path,
        globs=["README.md"],
        terms=["workflow"],
    )

    assert "README.md:1" not in report
    assert "README.md:2" not in report
    assert "README.md:4" not in report
    assert "`README.md:5` `workflow`" in report


def test_review_term_hints_scan_locale_text_but_not_js_selectors(monkeypatch, tmp_path: Path) -> None:
    write_source_lines(
        tmp_path,
        "src/loopora/static/pages/alignment.js",
        [
            'const preview = document.getElementById("bundle-preview-title");',
            'showStatus(target, localeText("方案文件预览失败。", "Bundle preview failed."));',
            "window.alert(pickText({",
            '  zh: "无法删除这个方案文件。",',
            '  en: "Unable to delete this bundle.",',
            "}));",
        ],
    )

    report = write_term_hints_report(
        monkeypatch,
        tmp_path,
        globs=["src/loopora/static/pages/*.js"],
        terms=["bundle"],
    )

    assert "alignment.js:1" not in report
    assert "`src/loopora/static/pages/alignment.js:2` `bundle`" in report
    assert "`src/loopora/static/pages/alignment.js:5` `bundle`" in report
    assert "document.getElementById" not in report


def test_review_term_hints_ignore_javascript_template_interpolation_identifiers(
    monkeypatch, tmp_path: Path
) -> None:
    write_source_lines(
        tmp_path,
        "src/loopora/static/pages/alignment.js",
        [
            'showStatus(target, localeText(`${workflow.step_count || 0} steps`, "Run flow"));',
            'showStatus(target, localeText(`Visible workflow ${count}`, "Run flow"));',
        ],
    )

    report = write_term_hints_report(
        monkeypatch,
        tmp_path,
        globs=["src/loopora/static/pages/*.js"],
        terms=["workflow"],
    )

    assert "alignment.js:1" not in report
    assert "`src/loopora/static/pages/alignment.js:2` `workflow`" in report
    assert "workflow.step_count" not in report


def test_review_term_hints_ignore_explicit_negative_positioning(monkeypatch, tmp_path: Path) -> None:
    write_source_lines(
        tmp_path,
        "README.md",
        [
            "Loopora is not a prompt pack.",
            "Loopora is not generic chat.",
            "Default users should not see raw YAML.",
            "This page exposes workflow controls.",
            "它不是 prompt 模板库。",
            "默认用户不应看到 YAML。",
        ],
    )

    report = write_term_hints_report(
        monkeypatch,
        tmp_path,
        globs=["README.md"],
        terms=["prompt pack", "generic chat", "YAML", "workflow controls", "prompt 模板库"],
    )

    assert "README.md:1" not in report
    assert "README.md:2" not in report
    assert "README.md:3" in report
    assert "README.md:4" in report
    assert "README.md:5" not in report
    assert "README.md:6" in report
