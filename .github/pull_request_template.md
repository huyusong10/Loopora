## Stable outcome

<!-- What user-visible behavior or long-lived boundary changes? -->

## Compatibility and risk

<!-- Note public command/route/schema changes, migration or rollback needs, security/data impact, and residual risk. -->

## Evidence

- [ ] `uv run loopora dev check`
- [ ] Relevant focused contract checks are listed below.
- [ ] `uv run pytest -q tests/checks/journeys` was run when Web behavior changed, or the reason it was not needed is stated.
- [ ] Generated `tmp/package-check` and `src/loopora.egg-info` are absent.
- [ ] Public diagnostics, if included, are limited to reviewed `loopora doctor --public-json --workdir "$PWD"` and `loopora --version` output.

Exact commands and results:

```text

```

## Documentation and cleanup

- [ ] Design, tests, public docs, and changelog match the resulting contract.
- [ ] No secrets, private paths, raw transcripts, private logs, or recovery artifacts are included.
- [ ] Obsolete tests, helpers, and generated artifacts in the touched boundary were removed.
