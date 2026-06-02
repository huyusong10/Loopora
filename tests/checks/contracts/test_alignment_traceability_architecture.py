from __future__ import annotations

from pathlib import Path

from loopora.alignment_traceability_categories import (
    agent_candidate_evidence_preference_categories,
    agent_candidate_fake_done_categories,
)
from loopora.alignment_traceability_rules import alignment_agent_candidate_tradeoff_issues


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alignment_traceability_risk_categories_have_dedicated_boundary() -> None:
    categories_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_categories.py").read_text(
        encoding="utf-8"
    )
    risk_categories_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_risk_categories.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert agent_candidate_fake_done_categories.__module__ == "loopora.alignment_traceability_risk_categories"
    assert agent_candidate_evidence_preference_categories.__module__ == "loopora.alignment_traceability_risk_categories"
    assert "from loopora.alignment_traceability_risk_categories import" in categories_source
    for marker in ("def agent_candidate_fake_done_categories", "def agent_candidate_evidence_preference_categories"):
        assert marker in risk_categories_source
        assert marker not in categories_source
    assert "alignment_traceability_risk_categories.py" in design_source


def test_alignment_traceability_terms_use_dedicated_catalog_boundary() -> None:
    terms_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_terms.py").read_text(encoding="utf-8")
    catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_term_catalog.py").read_text(
        encoding="utf-8"
    )
    generic_catalog_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_generic_term_catalog.py"
    ).read_text(encoding="utf-8")
    cjk_catalog_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_cjk_term_catalog.py").read_text(
        encoding="utf-8"
    )
    agent_catalog_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_agent_term_catalog.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert "from loopora.alignment_traceability_term_catalog import" in terms_source
    assert "from loopora.alignment_traceability_generic_term_catalog import" in catalog_source
    assert "from loopora.alignment_traceability_cjk_term_catalog import" in catalog_source
    assert "from loopora.alignment_traceability_agent_term_catalog import" in catalog_source
    for marker, source in (
        ("ALIGNMENT_TRACEABILITY_GENERIC_TERMS", generic_catalog_source),
        ("ALIGNMENT_LOOP_FIT_TRACEABILITY_GENERIC_TERMS", generic_catalog_source),
        ("ALIGNMENT_TRACEABILITY_CJK_STOP_CHARS", cjk_catalog_source),
        ("ALIGNMENT_TRACEABILITY_GENERIC_CJK_TERMS", cjk_catalog_source),
        ("ALIGNMENT_AGENT_CANDIDATE_GENERIC_TERMS", agent_catalog_source),
    ):
        assert marker in source
        assert marker in catalog_source
        assert f"{marker} =" not in terms_source
    for marker in (
        "def agent_candidate_traceability_terms",
        "def agreement_cjk_traceability_terms",
        "def agreement_repeated_cjk_traceability_terms",
        "def agreement_traceability_terms",
    ):
        assert marker in terms_source
        assert marker not in catalog_source
    assert "alignment_traceability_term_catalog.py" in design_source
    assert "alignment_traceability_generic_term_catalog.py" in design_source
    assert "alignment_traceability_cjk_term_catalog.py" in design_source
    assert "alignment_traceability_agent_term_catalog.py" in design_source


def test_alignment_agent_candidate_traceability_category_rules_have_dedicated_boundary() -> None:
    rules_source = (REPO_ROOT / "src" / "loopora" / "alignment_traceability_rules.py").read_text(encoding="utf-8")
    agent_candidate_rules_source = (
        REPO_ROOT / "src" / "loopora" / "alignment_traceability_agent_candidate_rules.py"
    ).read_text(encoding="utf-8")
    design_source = (REPO_ROOT / "design" / "contracts.md").read_text(encoding="utf-8")

    assert alignment_agent_candidate_tradeoff_issues.__module__ == (
        "loopora.alignment_traceability_agent_candidate_rules"
    )
    assert "from loopora.alignment_traceability_agent_candidate_rules import" in rules_source
    for marker in (
        "def alignment_agent_candidate_tradeoff_issues",
        "def alignment_agent_candidate_execution_strategy_issues",
        "def alignment_agent_candidate_residual_risk_policy_issues",
    ):
        assert marker in agent_candidate_rules_source
        assert marker not in rules_source
    assert "alignment_traceability_agent_candidate_rules.py" in design_source
