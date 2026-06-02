# Security Policy

Loopora is experimental local-first software. Security reports are still welcome, especially issues that could expose local credentials, workspace files, run artifacts, evidence records, adapter-managed files, or Web access tokens.

## Supported Versions

Only the current development line and the latest published release are in scope for security fixes. Older local state formats are not migrated in place unless the current design explicitly says so.

## Reporting A Vulnerability

Use GitHub private vulnerability reporting for this repository when it is available:

<https://github.com/huyusong10/Loopora/security/advisories/new>

If that channel is unavailable, open a public GitHub issue that only asks for a private reporting channel. Do not include exploit details, secrets, tokens, private logs, or sensitive workspace paths in a public issue.

Please include:

- Affected Loopora version or commit.
- Operating system and Python version.
- Whether the issue involves CLI, Web, Agent adapter files, `.loopora/` state, run artifacts, evidence records, or package distribution.
- Minimal reproduction steps that avoid real credentials and private project data.
- Expected impact and any known mitigation.

## Scope

In scope:

- Unauthorized access to local Web endpoints or artifacts.
- Secret, token, credential, or private-path disclosure through logs, events, package data, or generated files.
- Unsafe adapter-managed file writes or cleanup behavior.
- Package contents that expose unintended local state or generated artifacts.

Out of scope:

- Vulnerabilities in third-party Agent hosts, provider CLIs, browsers, or operating systems unless Loopora makes the issue worse.
- Reports that require sharing real credentials or private business data.
- Social engineering, spam, denial-of-service against public infrastructure, or broad automated scanning without a concrete Loopora issue.

## Security Automation

GitHub Dependabot tracks `uv` dependency and GitHub Actions updates. CodeQL runs for Python and JavaScript/TypeScript on the default development branch, pull requests to that branch, weekly scheduled scans, and manual dispatch.

Automated scans are triage inputs, not a guarantee that a release is vulnerability-free. Treat findings as project quality work and keep security-sensitive details in private reporting channels.

Loopora does not run a bounty program. Good-faith reports will be handled as project quality and safety work.
