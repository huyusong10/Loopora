from __future__ import annotations

from public_docs_test_support import ROOT, _assert_semantic_groups


def test_contributing_doc_keeps_local_quality_gates_and_boundary_rules_actionable() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    required_semantics = (
        ("Python 3.11", "uv", "Node.js"),
        (".editorconfig", ".gitattributes", "LF"),
        ("uv sync --locked",),
        ("uv run loopora dev check",),
        ("uv run loopora dev check --list",),
        ("uv run pytest tests/checks/journeys -q",),
        ("Dependency update pull requests", "uv", "GitHub Actions", "uv.lock"),
        ("CodeQL", "Python", "JavaScript/TypeScript"),
        ("bug report template", "feature request template", "SECURITY.md"),
        ("design/README.md", "design/contracts.md"),
        ("CLI output", "Web routes", "API payloads", "runner state"),
        ("observable contracts", "structured outputs", "accessible behavior"),
        ("license", "maintainer approval"),
    )

    _assert_semantic_groups(text, required_semantics, label="CONTRIBUTING.md")


def test_security_policy_keeps_private_reporting_and_local_risk_scope_actionable() -> None:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    required_semantics = (
        ("GitHub private vulnerability reporting",),
        ("security/advisories/new",),
        ("Do not include exploit details", "public issue"),
        ("local credentials", "workspace files", "run artifacts", "evidence records"),
        ("CLI", "Web", "Agent adapter files", ".loopora/"),
        ("package contents", "generated artifacts"),
        ("Dependabot", "uv", "GitHub Actions"),
        ("CodeQL", "Python", "JavaScript/TypeScript"),
        ("triage inputs", "vulnerability-free"),
        ("third-party Agent hosts", "out of scope"),
        ("bounty program", "Good-faith reports"),
    )

    _assert_semantic_groups(text, required_semantics, label="SECURITY.md")
