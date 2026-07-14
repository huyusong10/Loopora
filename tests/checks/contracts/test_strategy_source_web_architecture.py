from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_web_input_projection_uses_strategy_source_boundary_for_strategy_forms() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    web_inputs_source = (REPO_ROOT / "src" / "loopora" / "web_inputs.py").read_text(encoding="utf-8")
    web_strategy_inputs_source = (REPO_ROOT / "src" / "loopora" / "web_strategy_inputs.py").read_text(encoding="utf-8")
    web_loop_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_loop_pages.py").read_text(encoding="utf-8")
    web_orchestration_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_orchestration_pages.py").read_text(encoding="utf-8")
    web_spec_template_source = (REPO_ROOT / "src" / "loopora" / "web_spec_template_api_routes.py").read_text(encoding="utf-8")

    assert "def builtin_strategy_prompt_markdown_by_locale" in strategy_source_source
    assert "def normalize_strategy_prompt_locale" in strategy_source_source
    assert "from loopora.strategy_source import" not in web_inputs_source
    assert "from loopora.strategy_source import" in web_strategy_inputs_source
    assert "from loopora.workflows import" not in web_strategy_inputs_source
    assert "SpecTemplateStrategyCandidate" in web_strategy_inputs_source
    assert "SpecTemplateWorkflowCandidate" not in web_strategy_inputs_source
    assert "def _strategy_source_from_mapping" in web_strategy_inputs_source
    assert "def _workflow_from_mapping" not in web_strategy_inputs_source
    assert "def _strategy_source_for_spec_template" in web_strategy_inputs_source
    assert "def _strategy_source_for_spec_template_request" in web_strategy_inputs_source
    assert 'orchestration_id = str(payload.get("orchestration_id") or "").strip()' in web_strategy_inputs_source
    assert "def _workflow_for_spec_template" not in web_strategy_inputs_source
    assert "strategy_source = build_preset_strategy_source(preset_name)" in web_strategy_inputs_source
    assert "workflow = build_preset_strategy_source(preset_name)" not in web_strategy_inputs_source
    assert "strategy_source = strategy_source_from_record(orchestration) or {}" in web_strategy_inputs_source
    assert 'workflow = dict(orchestration.get("workflow_json") or {})' not in web_strategy_inputs_source
    assert "from loopora.web_strategy_inputs import" in web_inputs_source
    assert "_strategy_source_for_spec_template" in web_orchestration_pages_source
    assert "_strategy_source_for_spec_template" not in web_loop_pages_source
    assert "_workflow_for_spec_template" not in web_orchestration_pages_source + web_loop_pages_source
    assert "_strategy_source_for_spec_template_request" in web_spec_template_source
    assert "_workflow_for_spec_template" not in web_spec_template_source


def test_web_page_projections_use_strategy_source_boundary_for_strategy_display() -> None:
    strategy_source_source = (REPO_ROOT / "src" / "loopora" / "strategy_source.py").read_text(encoding="utf-8")
    web_overviews_source = (REPO_ROOT / "src" / "loopora" / "web_overviews.py").read_text(encoding="utf-8")
    web_projection_source = (REPO_ROOT / "src" / "loopora" / "web_projection.py").read_text(encoding="utf-8")
    web_route_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_loop_run_pages.py").read_text(encoding="utf-8")
    web_run_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_run_pages.py").read_text(encoding="utf-8")
    loop_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_loop_pages.py").read_text(encoding="utf-8")
    orchestration_pages_source = (REPO_ROOT / "src" / "loopora" / "web_route_context_orchestration_pages.py").read_text(encoding="utf-8")

    assert "def available_strategy_prompt_templates" in strategy_source_source
    assert "def strategy_source_from_record" in strategy_source_source
    assert "from loopora.strategy_source import" in web_projection_source
    assert "strategy_source_from_record" in web_projection_source
    assert "from loopora.strategy_source import" in orchestration_pages_source
    assert "from loopora.strategy_source import" not in loop_pages_source
    assert "from loopora.workflows import" not in "\n".join(
        [
            web_overviews_source,
            web_projection_source,
            loop_pages_source,
            orchestration_pages_source,
            web_route_pages_source,
            web_run_pages_source,
        ]
    )
    assert all(
        marker in web_overviews_source for marker in ("def _strategy_role_executor_summary", "def _overview_strategy_source", "strategy_source_from_record")
    )
    assert all(
        marker not in web_overviews_source
        for marker in (
            "def _workflow_role_executor_summary",
            'strategy_source = loop.get("workflow_json") or {}',
            'workflow = loop.get("workflow_json") or {}',
        )
    )
    assert "def web_run_detail_progress_stages" in web_projection_source
    assert "return ctx.render_loop_detail(request, loop_id)" in web_route_pages_source
    assert "_strategy_role_executor_summary" in web_run_pages_source
    assert "_overview_strategy_source(loop)" in web_run_pages_source
    assert all(
        marker in web_run_pages_source
        for marker in (
            "web_projection = self.svc().app_services.projection.web_run_detail(run)",
            '"progress_stages": web_projection["progress_stages"]',
        )
    )
    assert all(marker not in web_route_pages_source + web_run_pages_source for marker in ("_workflow_role_executor_summary", "_progress_stage_seed"))


def test_web_editor_and_form_routes_use_strategy_source_boundary_for_strategy_validation() -> None:
    spec_template_source = (REPO_ROOT / "src" / "loopora" / "web_spec_template_api_routes.py").read_text(encoding="utf-8")
    orchestration_forms_source = (REPO_ROOT / "src" / "loopora" / "web_orchestration_form_routes.py").read_text(encoding="utf-8")
    errors_source = (REPO_ROOT / "src" / "loopora" / "web_route_errors.py").read_text(encoding="utf-8")

    assert "from loopora.strategy_source import" in spec_template_source
    assert "from loopora.strategy_source import" in orchestration_forms_source
    assert "from loopora.strategy_source import" in errors_source
    assert "from loopora.workflows import" not in spec_template_source
    assert "from loopora.workflows import" not in orchestration_forms_source
    assert "from loopora.workflows import" not in errors_source
    assert "_role_note_sections_from_strategy_source" in spec_template_source
    assert "_role_note_sections_from_workflow" not in spec_template_source
    assert "strategy source validation error" in errors_source
