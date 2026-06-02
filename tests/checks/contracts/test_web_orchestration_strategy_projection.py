from __future__ import annotations

from web_static_projection_support import REPO_ROOT, STATIC_ROOT


def test_orchestration_surfaces_prefer_strategy_source_projection_names() -> None:
    new_loop_js = (STATIC_ROOT / "pages" / "new_loop.js").read_text(encoding="utf-8")
    new_orchestration_js = (STATIC_ROOT / "pages" / "new_orchestration.js").read_text(encoding="utf-8")
    orchestrations_js = (STATIC_ROOT / "pages" / "orchestrations.js").read_text(encoding="utf-8")
    new_orchestration_html = (REPO_ROOT / "src" / "loopora" / "templates" / "new_orchestration.html").read_text(
        encoding="utf-8"
    )
    orchestrations_html = (REPO_ROOT / "src" / "loopora" / "templates" / "orchestrations.html").read_text(
        encoding="utf-8"
    )

    assert "orchestration?.strategy_source || orchestration?.workflow_json || {}" in new_loop_js
    assert "strategy_json: selectedStrategySource" in new_loop_js
    assert "workflow_json: currentOrchestration()?.workflow_json" not in new_loop_js
    assert "strategy_json: workflowState" in new_orchestration_js
    assert 'name="strategy_json"' in new_orchestration_html
    assert "data-strategy-diagram" in orchestrations_html
    assert "data-workflow-diagram" not in orchestrations_html
    assert "[data-strategy-diagram], [data-workflow-diagram]" in orchestrations_js
