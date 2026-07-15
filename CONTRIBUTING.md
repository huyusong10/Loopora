# Contributing to Loopora

Loopora is experimental, but its documented behavior is contract-bearing. Start from [design/README.md](design/README.md), preserve the relevant stable boundary, and add evidence for observable behavior changes.

## Development Setup

Use Python 3.11 or newer, `uv`, and Node.js:

```bash
uv sync --locked
```

Before proposing a change, inspect and run the default gate:

```bash
uv run loopora dev check --list
uv run loopora dev check
```

The gate owns dependency checks, JavaScript syntax, Ruff, the accepted complexity budget, diff safety, distribution contents, contract tests, and package-output cleanup. After it finishes, `tmp/package-check` and `src/loopora.egg-info` must be absent.

Run the nearest behavior check for the boundary you changed. Web route, template, navigation, form, or browser-state changes also require:

```bash
uv run pytest -q tests/checks/journeys
```

Real provider and Agent-host probes are opt-in release evidence. Ordinary pull requests must not depend on live credentials, personal sessions, or remote provider state.

## Change Design

- Locate the stable boundary before editing implementation.
- Keep task-specific variation in reviewed data and generic compiler rules; do not add a module or dispatch table per business domain.
- Assert user-observable semantics, not private module layout or exact copy.
- Update design and tests when a public route, command, schema, security boundary, data format, or core journey changes.
- Prefer consolidation or deletion when docs, tests, or compatibility helpers duplicate the same claim.
- Preserve local path containment, secret redaction, non-loopback Web protection, and explicit confirmation for destructive actions.

## Pull Requests

Describe:

- the stable behavior being changed;
- compatibility or migration impact;
- exact checks run and their results;
- journey, review, or probe evidence when applicable;
- residual risks and intentionally skipped evidence.

Use only redacted public diagnostics in issues or pull requests:

```bash
loopora doctor --public-json --workdir "$PWD"
loopora --version
```

Review the output before posting it. Never paste tokens, private logs, raw model transcripts, local command history, absolute private paths, or private run/recovery archives.

## Release Readiness

Release readiness is maintainer-owned and is not an ordinary pull-request gate. For a candidate release:

1. Name the candidate tag and its support status under [SECURITY.md](SECURITY.md).
2. Run the default-fast gate and current browser journeys.
3. Run relevant real-host probes from their playbook.
4. Review the changelog for compatibility, migration, security, support, and distribution notes.
5. Confirm wheel/sdist contents and that generated package output was cleaned.
6. Preserve exact evidence results without publishing private machine or project data.

The repository currently declares no license. Do not add dependency, redistribution, contribution-rights, or release claims that assume one without maintainer approval.

## Style

Use LF line endings and UTF-8 text. Keep public docs clear in both English and Chinese where paired documentation exists. Commit messages should explain the stable outcome, not enumerate internal file moves.
