from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_score_history_coercion_has_shared_boundary() -> None:
    helper_source = (REPO_ROOT / "src" / "loopora" / "score_history_values.py").read_text(encoding="utf-8")
    stagnation_source = (REPO_ROOT / "src" / "loopora" / "stagnation.py").read_text(encoding="utf-8")
    summary_source = (REPO_ROOT / "src" / "loopora" / "runner_summary_projection.py").read_text(encoding="utf-8")
    iteration_log_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_log_entries.py").read_text(
        encoding="utf-8"
    )
    context_summary_source = (REPO_ROOT / "src" / "loopora" / "context_iteration_summary.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "def structured_score_values" in helper_source
    assert "structured_optional_finite_number" in helper_source
    for source in (stagnation_source, summary_source, iteration_log_source, context_summary_source):
        assert "from loopora.score_history_values import" in source
        assert "def _score_values" not in source
        assert "def _number_values" not in source
    assert "score_history_values.py" in contracts_source


def test_iteration_result_enrichment_has_dedicated_boundary() -> None:
    reporting_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_reporting.py").read_text(encoding="utf-8")
    log_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_log_entries.py").read_text(encoding="utf-8")
    summary_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_summary_markdown.py").read_text(
        encoding="utf-8"
    )
    enrichment_source = (REPO_ROOT / "src" / "loopora" / "service_iteration_result_enrichment.py").read_text(
        encoding="utf-8"
    )
    contracts_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.service_iteration_result_enrichment import" in reporting_source
    assert "from loopora.service_iteration_log_entries import" in reporting_source
    assert "from loopora.service_iteration_summary_markdown import" in reporting_source
    for marker in ("def enrich_tester_result", "def enrich_verifier_result", "def build_decision_summary"):
        assert marker in enrichment_source
        assert marker not in reporting_source
    for marker in ("def build_generator_log_entry", "def build_iteration_log_entry"):
        assert marker in log_source
        assert marker not in reporting_source + enrichment_source + summary_source
    for marker in (
        "def build_iteration_summary_markdown",
        "def format_inline_code_list",
        "def format_failure_refs",
        "def format_metric_refs",
    ):
        assert marker in summary_source
        assert marker not in reporting_source + enrichment_source + log_source
    for marker in ("def _build_iteration_log_entry", "def _build_summary", "def _format_inline_code_list"):
        assert marker in reporting_source
        assert marker not in enrichment_source
    assert "return build_iteration_log_entry(report)" in reporting_source
    assert "return build_iteration_summary_markdown(request, truncate_text=self._truncate_text)" in reporting_source
    assert "service_iteration_result_enrichment.py" in contracts_source
    assert "service_iteration_log_entries.py" in contracts_source
    assert "service_iteration_summary_markdown.py" in contracts_source
