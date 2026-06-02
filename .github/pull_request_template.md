## Summary

-

## Stable Boundary

- Touched boundary:
- Design updated or not needed because:

## Evidence

- [ ] `find src/loopora/static -name '*.js' -print0 | xargs -0 -n1 node --check`
- [ ] `uv pip check`
- [ ] `uv run ruff check src/loopora tests`
- [ ] `git diff --check`
- [ ] `rm -rf tmp/package-check`
- [ ] `mkdir -p tmp/package-check`
- [ ] `uv build --out-dir tmp/package-check`
- [ ] `uv run pytest -q tests/checks/contracts`
- [ ] Focused or journey checks for the touched area:

## Risk Notes

- [ ] This does not change license, distribution terms, public compatibility, permissions, credentials, or sensitive data handling without maintainer approval.
