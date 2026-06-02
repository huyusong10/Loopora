from __future__ import annotations

import tomllib
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
GITHUB_ROOT = REPO_ROOT / ".github"
CI_WORKFLOW = GITHUB_ROOT / "workflows" / "ci.yml"
CODEQL_WORKFLOW = GITHUB_ROOT / "workflows" / "codeql.yml"
DEPENDABOT_CONFIG = GITHUB_ROOT / "dependabot.yml"
UV_LOCK = REPO_ROOT / "uv.lock"
ISSUE_TEMPLATE_ROOT = GITHUB_ROOT / "ISSUE_TEMPLATE"
PULL_REQUEST_TEMPLATE = GITHUB_ROOT / "pull_request_template.md"
QUALITY_GATE_COMMANDS = (
    "find src/loopora/static -name '*.js' -print0 | xargs -0 -n1 node --check",
    "uv pip check",
    "uv run ruff check src/loopora tests",
    "git diff --check",
    "rm -rf tmp/package-check",
    "mkdir -p tmp/package-check",
    "uv build --out-dir tmp/package-check",
    "uv run pytest -q tests/checks/contracts",
)
CODEQL_TIMEOUT_MINUTES = 20
DEPENDABOT_OPEN_PULL_REQUEST_LIMIT = 5
DEPENDABOT_SCHEMA_VERSION = 2
EXPECTED_UV_SYNC_STEP_COUNT = 2


def _github_workflow_triggers(config: dict[object, object]) -> object:
    return config.get("on", config.get(True))


def _locked_package_version(name: str) -> str:
    lock = tomllib.loads(UV_LOCK.read_text(encoding="utf-8"))
    versions = [package["version"] for package in lock["package"] if package["name"] == name]

    assert len(versions) == 1
    return versions[0]


def test_github_yaml_files_are_parseable() -> None:
    parsed = {
        path.relative_to(REPO_ROOT): yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(GITHUB_ROOT.rglob("*.yml"))
    }

    assert parsed
    assert all(document for document in parsed.values())


def test_github_pull_request_template_keeps_boundary_and_evidence_prompts() -> None:
    template = PULL_REQUEST_TEMPLATE.read_text(encoding="utf-8")

    for term in (*QUALITY_GATE_COMMANDS, "Stable Boundary", "Design updated or not needed", "journey checks"):
        assert term in template
    for term in ("license", "maintainer approval"):
        assert term in template


def test_github_issue_templates_keep_public_reports_structured_and_security_safe() -> None:
    bug_report = yaml.safe_load((ISSUE_TEMPLATE_ROOT / "bug_report.yml").read_text(encoding="utf-8"))
    feature_request = yaml.safe_load((ISSUE_TEMPLATE_ROOT / "feature_request.yml").read_text(encoding="utf-8"))
    config = yaml.safe_load((ISSUE_TEMPLATE_ROOT / "config.yml").read_text(encoding="utf-8"))

    assert bug_report["name"] == "Bug Report"
    assert bug_report["labels"] == ["bug"]
    bug_text = (ISSUE_TEMPLATE_ROOT / "bug_report.yml").read_text(encoding="utf-8")
    for term in ("SECURITY.md", "credentials", "tokens", "private workspace paths", "Reproduction", "Affected Surface"):
        assert term in bug_text

    assert feature_request["name"] == "Feature Request"
    assert feature_request["labels"] == ["enhancement"]
    feature_text = (ISSUE_TEMPLATE_ROOT / "feature_request.yml").read_text(encoding="utf-8")
    for term in ("stable user-observable behavior", "public contract", "Evidence Or Examples", "Compatibility And Risk"):
        assert term in feature_text

    assert config["blank_issues_enabled"] is False
    assert config["contact_links"][0]["name"] == "Private Security Report"
    assert "security/advisories/new" in config["contact_links"][0]["url"]


def test_github_ci_workflow_keeps_default_quality_gate_contract() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    for term in (
        "name: CI",
        "pull_request:",
        "permissions:\n  contents: read",
        "group: ${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress: true",
        'python-version: ["3.11", "3.12"]',
        *QUALITY_GATE_COMMANDS,
        "uv run pytest tests/checks/journeys -q",
    ):
        assert term in workflow
    assert workflow.count("uv sync --locked") == EXPECTED_UV_SYNC_STEP_COUNT


def test_github_browser_journey_container_matches_locked_playwright_version() -> None:
    config = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
    container = config["jobs"]["browser-journey"]["container"]

    assert container["image"] == f"mcr.microsoft.com/playwright/python:v{_locked_package_version('playwright')}-noble"


def test_github_codeql_workflow_keeps_security_scan_scope_and_permissions_explicit() -> None:
    config = yaml.safe_load(CODEQL_WORKFLOW.read_text(encoding="utf-8"))

    assert config["name"] == "CodeQL"
    assert _github_workflow_triggers(config) == {
        "push": {"branches": ["dev"]},
        "pull_request": {"branches": ["dev"]},
        "schedule": [{"cron": "37 3 * * 1"}],
        "workflow_dispatch": None,
    }
    assert config["permissions"] == {"contents": "read", "security-events": "write"}
    assert config["concurrency"] == {"group": "${{ github.workflow }}-${{ github.ref }}", "cancel-in-progress": True}

    job = config["jobs"]["analyze"]
    assert job["timeout-minutes"] == CODEQL_TIMEOUT_MINUTES
    assert job["strategy"]["fail-fast"] is False
    assert job["strategy"]["matrix"]["include"] == [
        {"language": "javascript-typescript", "build-mode": "none"},
        {"language": "python", "build-mode": "none"},
    ]

    steps = job["steps"]
    assert steps[0] == {"name": "Checkout", "uses": "actions/checkout@v6"}
    assert steps[1] == {
        "name": "Initialize CodeQL",
        "uses": "github/codeql-action/init@v4",
        "with": {"languages": "${{ matrix.language }}", "build-mode": "${{ matrix.build-mode }}"},
    }
    assert steps[2] == {"name": "Perform CodeQL analysis", "uses": "github/codeql-action/analyze@v4"}


def test_github_dependabot_keeps_dependency_update_prs_scoped_and_scheduled() -> None:
    config = yaml.safe_load(DEPENDABOT_CONFIG.read_text(encoding="utf-8"))

    assert config["version"] == DEPENDABOT_SCHEMA_VERSION
    updates = config["updates"]
    update_by_ecosystem = {entry["package-ecosystem"]: entry for entry in updates}

    assert set(update_by_ecosystem) == {"uv", "github-actions"}
    for entry in update_by_ecosystem.values():
        assert entry["directory"] == "/"
        assert entry["schedule"] == {"interval": "weekly", "day": "monday", "time": "09:00", "timezone": "Etc/UTC"}
        assert entry["open-pull-requests-limit"] == DEPENDABOT_OPEN_PULL_REQUEST_LIMIT
