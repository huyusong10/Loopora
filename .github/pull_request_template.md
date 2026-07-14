## Summary

-

## Change Type

- [ ] Bug fix or setup/readiness blocker
- [ ] User-visible feature or workflow change
- [ ] Documentation, support, or contributor experience
- [ ] Internal refactor with preserved public behavior
- [ ] Release, packaging, security, license, or distribution-sensitive change

## Stable Behavior

- User-visible behavior or public contract this preserves or improves:
- Why this is the right product/maintainability tradeoff now:

## Boundary And Design

- Touched stable boundary:
- Design updated, or not needed because:

## Risk Level

- [ ] Low: internal, reversible, and does not change public contracts, persisted data, permissions, security, accessibility, localization, core journeys, migration cost, or rollback difficulty.
- [ ] Elevated: changes one of those boundaries, and the maintainer-approved compatibility/migration/rollback plan is noted here:

## Evidence

- [ ] Decision scope evidence was collected before choosing or finalizing checks. Use `uv run loopora dev check --list --pr-evidence` while planning, then paste the final `### Loopora PR Evidence` block from `uv run loopora dev check --pr-evidence` (`template_markdown` in JSON, or the plain copyable block):
- The pasted block must include decision scope evidence, evidence stage, public-safe evidence command source, changed-file detection, recommended focused guide IDs, unmatched/ignored changed files, focused guide IDs run including any `--focused-ran` declaration, skipped guide IDs, final dev-check result, and package-build cleanup for `tmp/package-check` and `src/loopora.egg-info`:
- Journey, review, or probe checks if user flow, browser behavior, provider behavior, or Agent host integration changed:
- Skipped recommended or boundary-relevant guide IDs, and why:

## Public Safety

- [ ] Issue/PR-facing readiness evidence pastes the public issue support bundle first when readiness or environment evidence matters. Paste public doctor/version output only when lower-level evidence or identity is requested, using `loopora version --json` only when structured identity is requested, not local command lines or local Web Support URLs. Run `loopora support --workdir "$PWD" --public-issue-bundle`, `loopora doctor --public-json --workdir "$PWD"`, or an equivalent redacted report locally when relevant, with the same `--web-host` / `--web-port` flags for custom Web targets.
- [ ] Any public command or path examples use placeholders such as `<project-dir>`, `<Loopora checkout>`, or `<redacted>` instead of real local paths.
- [ ] This PR does not publish secrets, tokens, private workspace paths, private logs, sensitive run artifacts, or exploit details; security issues follow SECURITY.md.
- [ ] This does not change license, distribution terms, public compatibility, permissions, credentials, or sensitive data handling without maintainer approval.
