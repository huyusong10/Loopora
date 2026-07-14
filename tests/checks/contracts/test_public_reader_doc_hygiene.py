from __future__ import annotations

from public_docs_test_support import (
    CHINESE_PUBLIC_INTERNAL_TERM_PATTERN,
    CHINESE_PUBLIC_READER_DOCS,
    INLINE_REVIEW_NOTE_PATTERN,
    PUBLIC_DOC_MAX_LINE_LENGTH,
    PUBLIC_READER_DOCS,
    ROOT,
    _assert_semantic_groups,
)


def test_public_reader_docs_do_not_ship_inline_review_notes() -> None:
    for doc in PUBLIC_READER_DOCS:
        text = doc.read_text(encoding="utf-8")
        leaked_notes = INLINE_REVIEW_NOTE_PATTERN.findall(text)

        assert not leaked_notes, f"{doc.relative_to(ROOT)} exposes inline review notes: {leaked_notes[:3]}"


def test_chinese_public_reader_docs_use_reader_level_runtime_language() -> None:
    for doc in CHINESE_PUBLIC_READER_DOCS:
        text = doc.read_text(encoding="utf-8")
        internal_terms = sorted(set(CHINESE_PUBLIC_INTERNAL_TERM_PATTERN.findall(text)))

        assert not internal_terms, f"{doc.relative_to(ROOT)} exposes internal runtime terms: {internal_terms[:5]}"


def test_public_reader_docs_keep_public_contracts_readable() -> None:
    for doc in PUBLIC_READER_DOCS:
        long_lines = [
            (index, len(line))
            for index, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1)
            if len(line) > PUBLIC_DOC_MAX_LINE_LENGTH
        ]

        assert not long_lines, f"{doc.relative_to(ROOT)} has oversized public-reader lines: {long_lines[:3]}"


def test_code_of_conduct_keeps_public_collaboration_safe_and_scope_limited() -> None:
    text = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
    required_semantics = (
        ("Code of Conduct", "experimental local-first", "public collaboration", "respectful", "safe", "evidence-oriented"),
        ("repository issues", "pull requests", "reviews", "discussions", "release notes"),
        ("Expected Behavior", "respectful", "specific", "constructive"),
        ("Critique ideas", "evidence", "risks", "tradeoffs", "rather than people"),
        (
            "redacted",
            "secrets",
            "tokens",
            "private logs",
            "private workspace paths",
            "exploit details",
            "sensitive run artifacts",
        ),
        ("SUPPORT.md", "SECURITY.md", "GOVERNANCE.md"),
        ("affected workflow", "stable behavior", "evidence", "risk"),
        ("Unacceptable Behavior", "Harassment", "threats", "personal attacks", "discriminatory language", "sustained disruption"),
        ("Publishing private data", "credentials", "exploit details", "sensitive workspace information"),
        (
            "Pressuring contributors",
            "bypass security reporting",
            "evidence",
            "review",
            "migration",
            "compatibility",
            "license/distribution",
        ),
        ("Reporting And Enforcement", "security-sensitive", "SECURITY.md", "do not post details publicly"),
        ("private maintainer contact", "without naming private details"),
        ("Maintainers may", "edit or remove public comments", "close or lock discussions", "restrict participation"),
        ("proportionate", "documented", "not to expose private or security-sensitive information"),
        ("Scope Limits", "does not create", "support response-time guarantee", "license grant", "legal process", "moderation promise"),
        ("third-party Agent hosts", "provider services", "operating systems", "private projects"),
    )

    _assert_semantic_groups(text, required_semantics, label="CODE_OF_CONDUCT.md")


def test_governance_keeps_maintainer_decision_rights_and_escalation_explicit() -> None:
    text = (ROOT / "GOVERNANCE.md").read_text(encoding="utf-8")
    required_semantics = (
        ("Governance", "experimental local-first", "approve public project decisions", "evidence"),
        ("Decision Owners", "Loopora maintainers", "merge", "release", "security", "package-publishing"),
        ("maintainer approval", "public contract", "public project posture"),
        ("Supported release tags", "release readiness", "release notes", "package distribution"),
        ("License status", "redistribution terms", "third-party code intake", "reuse rights"),
        ("Security reporting channels", "private vulnerability handling", "public disclosure timing"),
        ("Compatibility", "migration", "rollback", "data handling", "permissions", "accessibility", "localization", "core user-journey"),
        ("design/contracts.md", "stable design boundaries", "tests or docs"),
        ("Contribution Path", "stable behavior", "evidence", "risk level", "affected design boundary"),
        ("SUPPORT.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "CHANGELOG.md", "CONTRIBUTING.md", "design/contracts.md"),
        ("Escalation Rules", "CLI/Web/API behavior", "package contents", "security posture", "license posture", "distribution terms"),
        ("user data", "local workspace safety", "tokens", "private paths", "run artifacts", "adapter-managed files"),
        ("review/probe/scenario evidence", "focused/default-fast checks"),
        ("secrets", "exploit details", "private logs", "sensitive workspace paths", "SECURITY.md"),
        ("Current Limits", "does not declare a license", "does not guarantee support response time"),
        ("public repository access", "redistribution", "reuse", "third-party intake rights", "explicit maintainer approval"),
    )

    _assert_semantic_groups(text, required_semantics, label="GOVERNANCE.md")


def test_changelog_keeps_public_release_history_and_adoption_risk_explicit() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    required_semantics = (
        ("Changelog", "public history entry", "user-visible changes", "adoption-risk notes", "release evidence"),
        ("not a support promise", "license grant", "SECURITY.md"),
        ("Unreleased", "does not yet publish a supported release tag", "current development line"),
        (
            "source checkout changes",
            "experimental",
            "verify",
            "release evidence commands preserve the release workdir",
            "First-use routing",
            "same-Agent setup/readiness comes before paste-ready handoff",
            "direct-path stop/record option",
        ),
        ("Public Adoption Notes", "best-effort", "no guaranteed response time", "supported security scope"),
        (
            "Public Adoption Notes",
            "public issue support bundle",
            "doctor --public-json",
            "loopora --version",
            "loopora version --json",
            "structured identity",
        ),
        ("does not declare a license", "redistribution", "reuse", "third-party intake"),
        ("Release Note Requirements", "Version or tag", "release date", "supported"),
        ("User-visible changes", "affected workflow", "public contract"),
        ("Compatibility", "migration", "rollback", "support", "security", "distribution risks"),
        (
            "Verification evidence",
            "focused guide IDs",
            "uv run loopora dev check",
            "browser journey",
            "skipped probes",
            "residual risks",
            "package-build cleanup",
        ),
        ("Private details", "intentionally omitted", "secrets", "exploit details", "private paths", "private logs", "sensitive run artifacts"),
    )

    _assert_semantic_groups(text, required_semantics, label="CHANGELOG.md")


def test_security_policy_keeps_private_reporting_and_local_risk_scope_actionable() -> None:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    required_semantics = (
        ("Supported Versions", "Security support"),
        ("source-only alpha boundary", "long-term support", "source snapshot"),
        ("GitHub private vulnerability reporting",),
        ("security/advisories/new",),
        ("Current development line", "reproduced against current source"),
        ("Release tags explicitly marked as supported by maintainers", "documented by maintainers"),
        ("Source-only development snapshots", "forks", "dirty checkouts", "unmarked tags"),
        ("No implied security support", "current development line", "supported release tag"),
        ("Older `.loopora/` local state formats", "current design"),
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


def test_support_policy_routes_help_without_public_private_data() -> None:
    text = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    required_semantics = (
        ("best-effort", "no guaranteed response time", "current development line", "supported"),
        ("loopora support", "safe public reporting route", "without running diagnostics or changing files"),
        ("loopora support --language zh", "human guidance in Chinese", "stable route kinds", "command execution blockers"),
        ("Web route", "top navigation", "/support", "public issue support bundle", "Same-Agent Setup", "Support and safe reporting"),
        ("loopora doctor --workdir",),
        (
            "loopora --version",
            "compact package/source identity",
            "loopora version --json",
            "structured data",
            "doctor",
            "readiness and recovery details",
        ),
        ("loopora support --workdir \"$PWD\" --public-issue-bundle", "human-readable", "readiness summary", "doctor --public-json"),
        ("Bare `loopora support`", "preview-only", "support --workdir", "public issue bundle or redacted report command becomes ready", "supplied target", "missing or not a directory", "redacted evidence", "setup remains not ready", "custom Web host or port", "--web-host", "--web-port"),
        ("custom Web host or port", "matching local Web Support page", "target project context", "local-only"),
        ("uv --directory <Loopora checkout> run loopora support --workdir", "public-issue-bundle", "target project"),
        ("preferred bundle directly", "source checkout before install", "doctor --public-json", "lower-level readiness evidence"),
        ("Run support commands locally", "public issue support bundle first", "requested redacted report/version output", "not command lines", "local checkout or project paths"),
        ("Keep local only", "Local Web Support URLs printed by support"),
        ("loopora support --json", "route metadata", "public issue attachment", "command fields", "local checkout or project paths"),
        (
            "Public diagnostic material allowlist",
            "Paste only",
            "doctor --public-json",
            "loopora --version",
            "loopora version --json",
            "structured identity",
        ),
        ("Loopora version", "source revision/dirty state", "operating system", "Python version", "Agent host"),
        ("credentials", "tokens", "provider transcripts", "private logs", "local paths", "local command lines", "sensitive workspace data"),
        ("Bug Report template", "report scope", "impact/workaround", "public readiness report status"),
        ("Bug Report template", "https://github.com/huyusong10/Loopora/issues/new?template=bug_report.yml"),
        ("Feature Request template", "Loopora fit", "non-goals", "adoption impact", "success criteria", "evidence", "compatibility risk"),
        ("Feature Request template", "first-use", "Web", "readiness", "package identity", "environment behavior"),
        ("public readiness report status", "public issue support bundle first", "doctor --public-json", "lower-level readiness evidence", "do not paste", "command line"),
        ("Feature Request template", "https://github.com/huyusong10/Loopora/issues/new?template=feature_request.yml"),
        ("Security vulnerabilities", "private vulnerability reporting", "SECURITY.md", "https://github.com/huyusong10/Loopora/security/advisories/new"),
        ("private channel is unavailable", "public issue only asking for a private reporting channel", "no exploit details or sensitive data"),
        ("setup blocker", "bug report", "new behavior", "feature request"),
        ("CLI/Web behavior", "managed Agent entry files", ".loopora/", "run artifacts", "evidence records", "package contents"),
        ("third-party Agent host", "provider CLI", "browser", "operating system", "unless Loopora makes the issue worse"),
    )

    _assert_semantic_groups(text, required_semantics, label="SUPPORT.md")
