from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.journey

ROOT = Path(__file__).resolve().parents[3]


def _review_runner():
    path = ROOT / "tests" / "reviews" / "run.py"
    spec = importlib.util.spec_from_file_location("loopora_review_runner_for_layout_hints", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_web_layout_hints_ignore_collapsed_details_content_but_keep_open_content() -> None:
    runner = _review_runner()
    html = """<!doctype html>
    <details>
      <summary>Open examples</summary>
      <button data-testid="example-card" style="width: 24px; height: 40px; overflow: hidden;">
        This long example card is intentionally too narrow.
      </button>
    </details>
    """

    with playwright.sync_playwright() as playwright_driver:
        browser = playwright_driver.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 420, "height": 360})
            page.set_content(html, wait_until="load")
            collapsed_hints = page.evaluate(runner.WEB_LAYOUT_HINT_SCRIPT)
            page.locator("details").evaluate("element => element.open = true")
            open_hints = page.evaluate(runner.WEB_LAYOUT_HINT_SCRIPT)
        finally:
            browser.close()

    assert not any("example-card" in hint for hint in collapsed_hints)
    assert any("example-card" in hint for hint in open_hints)
