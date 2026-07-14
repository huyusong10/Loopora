# Governance

Loopora is experimental local-first software. Governance here is deliberately small: it names who can approve public project decisions, which changes need maintainer review, and which evidence keeps those decisions auditable.

## Decision Owners

Loopora maintainers are the people with repository merge, release, security, or package-publishing authority. Contributors can propose changes through issues and pull requests, but maintainer approval is required before a proposal changes a public contract or public project posture.

Maintainer-owned decisions include:

- Supported release tags, release readiness, release notes, and package distribution.
- License status, redistribution terms, third-party code intake, and any metadata that implies reuse rights.
- Security reporting channels, private vulnerability handling, and public disclosure timing.
- Compatibility, migration, rollback, data handling, permissions, accessibility, localization, or core user-journey changes.
- Stable design boundaries in [design/contracts.md](./design/contracts.md), especially when tests or docs need to change with implementation.

## Contribution Path

Small internal changes can proceed with the normal pull request checklist in [CONTRIBUTING.md](./CONTRIBUTING.md). Larger changes should make the stable behavior, evidence, risk level, and affected design boundary explicit before implementation review.

Use these public assets as the decision trail:

- [SUPPORT.md](./SUPPORT.md) routes usage, setup, bug, feature, and security-sensitive reports.
- [SECURITY.md](./SECURITY.md) owns private vulnerability reporting and supported security scope.
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) owns public collaboration behavior and conduct escalation.
- [CHANGELOG.md](./CHANGELOG.md) owns public change history, adoption-risk notes, and release-note requirements.
- [CONTRIBUTING.md](./CONTRIBUTING.md) owns local quality gates, focused evidence, and pull request evidence.
- [design/contracts.md](./design/contracts.md) owns stable product and implementation boundaries.

## Escalation Rules

Ask for maintainer approval before merging or documenting changes that:

- Add, remove, or reinterpret public CLI/Web/API behavior.
- Change package contents, release support status, security posture, license posture, or distribution terms.
- Touch user data, local workspace safety, permissions, tokens, private paths, run artifacts, evidence records, or adapter-managed files.
- Require migrations, irreversible cleanup, difficult rollback, or user-visible compatibility tradeoffs.
- Need review/probe/scenario evidence beyond focused/default-fast checks.

If a discussion exposes secrets, exploit details, private logs, or sensitive workspace paths, stop using public channels and follow [SECURITY.md](./SECURITY.md).

## Current Limits

This repository currently does not declare a license and does not guarantee support response time. Public repository access does not grant redistribution, reuse, or third-party intake rights. Governance changes that alter those limits require explicit maintainer approval and matching updates to the affected public docs, package metadata, design boundary, and tests.
