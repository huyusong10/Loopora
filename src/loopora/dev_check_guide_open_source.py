from __future__ import annotations

from loopora.dev_check_guide_types import FocusedCheckGuide


OPEN_SOURCE_COLLABORATION_GUIDE = FocusedCheckGuide(
    id="open_source_collaboration",
    label="Open-source collaboration and distribution",
    when=(
        "Contributor docs, design map, GitHub templates/workflows, security guidance, review/scenario evidence "
        "workflows, package contents, or default gate behavior changed."
    ),
    command="uv run pytest -q tests/checks/contracts/test_public_open_source_docs.py "
    "tests/checks/contracts/test_public_agent_native_docs.py "
    "tests/checks/contracts/test_public_reader_doc_hygiene.py "
    "tests/checks/contracts/test_package_metadata.py "
    "tests/checks/contracts/test_github_collaboration.py "
    "tests/checks/contracts/test_public_svg_asset_integrity.py "
    "tests/checks/contracts/test_public_svg_distribution_docs.py "
    "tests/checks/contracts/test_review_runner_case_targets.py "
    "tests/checks/contracts/test_review_runner_text_indexes.py "
    "tests/checks/contracts/test_review_runner_term_hints.py "
    "tests/checks/contracts/test_cli_dev_reset.py "
    "tests/checks/contracts/test_verification_map.py "
    "tests/checks/contracts/test_dev_check_guide_catalog_architecture.py "
    "tests/checks/contracts/test_design_contract_docs.py "
    "tests/checks/contracts/test_real_probe_workflow.py",
    evidence_type="focused",
    path_patterns=(
        ".github/",
        "assets/diagrams/",
        "src/loopora/assets/demo/",
        "src/loopora/assets/logo/",
        "design/",
        "CODE_OF_CONDUCT.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "README.md",
        "README.zh-CN.md",
        "SECURITY.md",
        "SUPPORT.md",
        "HUMAN-SHAPED-LOOP*",
        "MANIFEST.in",
        "setup.py",
        "pyproject.toml",
        "uv.lock",
        "tests/README.md",
        "tests/reviews/",
        "tests/scenarios/",
        "src/loopora/dev_check*.py",
        "src/loopora/package_source_provenance.py",
        "src/loopora/cli_dev*.py",
        "src/loopora/cli_support_output.py",
        "src/loopora/diagnose_doctor_public*.py",
        "src/loopora/support_guidance*.py",
        "src/loopora/support_issue_bundle.py",
        "tests/checks/contracts/public_docs_test_support.py",
        "tests/checks/contracts/review_runner_test_support.py",
        "tests/checks/contracts/cli_dev_command_test_support.py",
        "tests/checks/contracts/test_public_agent_native_docs.py",
        "tests/checks/contracts/test_public_open_source_docs.py",
        "tests/checks/contracts/test_public_reader_doc_hygiene.py",
        "tests/checks/contracts/test_package_metadata.py",
        "tests/checks/contracts/test_public_svg_asset_integrity.py",
        "tests/checks/contracts/test_public_svg_distribution_docs.py",
        "tests/checks/contracts/test_review_runner*.py",
        "tests/checks/contracts/test_github_collaboration.py",
        "tests/checks/contracts/test_cli_dev_reset.py",
        "tests/checks/contracts/test_dev_check_guide_catalog_architecture.py",
        "tests/checks/contracts/design_contract_docs_public_web_checks.py",
        "tests/checks/contracts/test_design_contract_docs*.py",
        "tests/checks/contracts/test_real_probe_workflow.py",
        "tests/checks/contracts/test_verification_map.py",
    ),
)


__all__ = ("OPEN_SOURCE_COLLABORATION_GUIDE",)
