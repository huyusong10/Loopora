# Contributing to Loopora

Loopora is still experimental, but contributions should treat its public behavior as contract-bearing. Keep changes grounded in the current design map, add evidence for behavior changes, and avoid turning implementation details into stable promises.

## Development Setup

Use Python 3.11 or newer, `uv`, and Node.js for static JavaScript syntax checks.

```bash
uv sync --locked
```

The repository declares editor and Git text normalization through `.editorconfig` and `.gitattributes`; use LF line endings and keep files UTF-8 encoded unless a binary format requires otherwise.

Run the same fast gates used by CI before proposing a change:

```bash
uv run loopora dev check
```

Use `uv run loopora dev check --list` to inspect the expanded default-fast steps without running them.

Browser journey checks are part of CI and should be run for Web behavior, route changes, templates, static assets, or anything that affects a user flow:

```bash
uv run pytest tests/checks/journeys -q
```

Real provider and real Agent probes are opt-in release evidence. Do not make ordinary pull requests depend on live credentials, host-specific sessions, or remote provider state.

Dependency update pull requests are automated for `uv` dependencies and GitHub Actions. They still need the same fast gates and any focused checks for the touched boundary, and CI installs with `uv sync --locked` so dependency changes must keep `uv.lock` consistent.

CodeQL scans Python and JavaScript/TypeScript as repository security automation. Treat CodeQL findings as triage evidence for the affected stable boundary, and keep exploit details or secrets out of public pull requests and issues.

## Reporting Issues

Use the GitHub bug report template for reproducible defects and the feature request template for proposed user-visible behavior. Security-sensitive reports must follow [SECURITY.md](SECURITY.md) instead of public issues.

## Design And Test Boundaries

Start from [design/README.md](design/README.md). It points to the current stable boundary map, especially [design/contracts.md](design/contracts.md).

Use this rule of thumb:

- Internal refactors should preserve public behavior and keep existing contract tests passing.
- Changes to CLI output, Web routes, API payloads, runner state, persisted records, evidence semantics, task verdicts, adapter entries, or user-visible flows need matching tests.
- Changes that introduce or alter a stable boundary should update the relevant design entry in the same pull request.
- Tests should assert observable contracts, structured outputs, errors, durable artifacts, or accessible behavior. Avoid locking private helpers, DOM structure, CSS classes, exact prose, or incidental object ordering.

## Pull Request Checklist

Before opening a pull request:

- Read the relevant design entry and nearby tests.
- Keep the diff scoped to one stable boundary when possible.
- Add or update tests for behavior changes.
- Run the focused tests for the touched area plus the fast gates above.
- Note any skipped checks and why they were not applicable.

## Project Governance

This repository currently does not declare a license. Do not add license metadata, copy third-party code, or change distribution terms without explicit maintainer approval.
