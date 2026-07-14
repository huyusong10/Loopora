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

The default gate owns package-build cleanup as well as checks. After the gate passes or fails, `tmp/package-check` and `src/loopora.egg-info` should be absent; remove those generated paths yourself if you inspected package artifacts manually before collecting final PR evidence.
Plain default-fast and PR evidence runs print `progress:` lines while commands execute, so long package-build or contract-check phases should not look frozen. Use `--json` for automation when stdout must stay machine-parseable.

Use `uv run loopora dev check --list` to inspect the expanded default-fast steps, focused selector choices,
the focused check guide, recommended focused checks, and changed files that do not match any focused guide for
the current Git changes, including non-ignored untracked files, without running them. Add `--pr-evidence` when you want a template-ready Markdown block headed `### Loopora PR Evidence`
for the pull request instead of the full guide; JSON callers receive the same block as
`pr_evidence_summary.template_markdown` plus an `evidence_stage` such as `decision`, `focused_passed`, or
`default_fast_passed`.

On the final evidence command, pass `--focused-ran recommended` or explicit guide IDs when those focused checks
already passed so the copyable block does not require manual merging. Explicit changed paths can be passed with
`--changed-file` or as trailing path arguments; paths outside `--workdir` or parent-relative paths are reported
as ignored changed files instead of driving recommendations.
When changed files exist and no provided inputs were ignored, plain output says `ignored changed files: none`;
when every changed path matched a focused guide, it says `unmatched changed files: none`. Record both lines
directly in PR evidence. After the selected focused checks cover the recommended boundary, the next-action output
includes a final PR evidence command with the passed guide IDs already attached. If an explicit focused run covers
only part of the recommended boundary, its next action points to the remaining recommended guide IDs and carries the
already-passed guide IDs forward before final evidence.

Plain output also prints a `PR evidence:` reminder before the command list so reviewers can see the decision
evidence was collected before checks were chosen. `loopora dev check --help` and `--list` both expose the
current selectors: `recommended`, `all`, and the guide IDs. When recommendations exist, run them directly:

```bash
uv run loopora dev check --focused recommended
```

Pick focused checks from the touched stable boundary rather than from the number of files changed. The `--list` recommendation is a starting point from changed paths; unmatched changed files must be reviewed for additional focused, journey, review, or probe evidence when they affect a stable boundary. Repeat `--focused <guide-id>` or comma-separate guide IDs when product risk crosses file ownership. Let `uv run loopora dev check --list` print the current expanded pytest commands instead of copying static file lists from this document.

| Guide ID | Stable boundary | Command |
| --- | --- | --- |
| `first_use_readiness` | First-use readiness, `doctor`, adapter setup, App/Web reset, resource commands, spec prompts | `uv run loopora dev check --focused first_use_readiness` |
| `web_surfaces` | Web routes, templates, diagnostics APIs, browser state, static assets, native path actions | `uv run loopora dev check --focused web_surfaces` |
| `agent_native` | Agent Native `/loopora-plan` or `/loopora-run` surfaces and context recovery | `uv run loopora dev check --focused agent_native` |
| `alignment_bundle` | Alignment dialogue, bundle candidates, READY validation, traceability, bundle exchange, Strategy Source files | `uv run loopora dev check --focused alignment_bundle` |
| `core_execution` | Kernel/Event Core, context schema, executor/provider profiles | `uv run loopora dev check --focused core_execution` |
| `runtime_state` | Run lifecycle, run observation, Loop deletion, file/artifact access, background worker, DB run records, settings/local App state | `uv run loopora dev check --focused runtime_state` |
| `open_source_collaboration` | Contributor docs, design map, GitHub templates/workflows, review/scenario evidence workflows, package contents | `uv run loopora dev check --focused open_source_collaboration` |

Browser journey checks are part of CI and should be run for Web behavior, route changes, templates, static assets, or anything that affects a user flow:

```bash
uv run pytest tests/checks/journeys -q
```

Real provider and real Agent probes are opt-in release evidence. Do not make ordinary pull requests depend on live credentials, host-specific sessions, or remote provider state.
Maintainers can run the GitHub Actions `Real Probe` workflow manually through `workflow_dispatch`; its default `release` suite is release-readiness evidence, and broader `real-agent`, `real-cli`, or `release-web` selections should stay tied to an explicit release or integration investigation. Failed or skipped workflow runs upload the `.loopora/real-probes/` reports as a GitHub artifact so maintainers can review phase evidence without relying on quiet stdout. Keep probe logs redacted and summarize skipped host/provider setup instead of turning secrets or private sessions into public PR evidence.

## Release Readiness

Release readiness is maintainer-owned evidence, not an ordinary pull request gate. Use it when preparing a supported release tag, distribution artifact, or public release notes; ordinary PRs should still use focused/default-fast evidence for the touched stable boundaries.

For a release candidate:

- Start from the Loopora checkout with `uv run loopora dev release-plan --candidate <version-or-tag> --supported-status supported|unsupported` to print the read-only release evidence plan. Add `--probe-ref <branch-or-tag>` when the candidate version is not the Git ref that should dispatch release probes. The command blocks on an unusable `--workdir`, missing candidate, or missing support status before emitting evidence commands that would fail later or be incomplete; it does not run checks, publish artifacts, or decide support status for maintainers.
- Copy the release-plan evidence commands as printed. They preserve the release workdir, so default-fast, focused, final PR evidence, and conditional journey checks run against the intended checkout even when the plan was generated through a source-checkout command from another shell directory.
- Name the candidate version or tag and whether maintainers intend to mark it as supported under [SECURITY.md](SECURITY.md).
- Run `uv run loopora dev check --list --pr-evidence` while planning, then `uv run loopora dev check --focused recommended`, any additional boundary-relevant focused guides, and the final `uv run loopora dev check --pr-evidence --focused-ran recommended` command from the release plan. Preserve the final `### Loopora PR Evidence` block with the release notes so default-fast, focused, changed-file scope, and package-cleanup evidence stay together.
- Run browser journey checks for touched Web behavior, and keep review or probe evidence tied to the affected boundary instead of expanding every release into a scenario run.
- Run the GitHub Actions `Real Probe` workflow through `workflow_dispatch` on the release probe ref with the default `release` suite. Preserve the `.loopora/real-probes/` artifact or summarize why host/provider setup was skipped; use broader suites only for explicit integration investigations.
- Treat package contents as part of the public contract: the default `package_build` step checks wheel and sdist runtime assets, public docs, metadata, entry points, and the current no-license boundary. Clean generated `tmp/package-check` or `src/loopora.egg-info` artifacts after any manual packaging inspection.
- Update [CHANGELOG.md](CHANGELOG.md): move relevant unreleased entries into the version section, state supported status, user-visible changes, verification evidence, skipped probes, residual risks, and any compatibility or security-sensitive details kept private. Do not publish secrets, private paths, private logs, exploit details, or distribution-term changes.

Dependency update pull requests are automated for `uv` dependencies and GitHub Actions. They still need the same fast gates and any focused checks for the touched boundary, and CI installs with `uv sync --locked` so dependency changes must keep `uv.lock` consistent.

CodeQL scans Python and JavaScript/TypeScript as repository security automation. Treat CodeQL findings as triage evidence for the affected stable boundary, and keep exploit details or secrets out of public pull requests and issues.

## Reporting Issues

Use [SUPPORT.md](SUPPORT.md) to choose the best-effort help path before filing.
Then choose the public template by the user-visible outcome:

- Bug reports use the GitHub bug report template for reproducible defects.
  Select a report scope and describe impact/workaround so maintainers can
  distinguish a Loopora behavior regression, setup/readiness blocker, upstream Agent/OS/tool issue made worse by Loopora, or uncertain case before asking for
  deeper diagnostics.
- Feature proposals use the GitHub feature request template for proposed
  user-visible behavior. Explain why Loopora is the right owner instead of
  direct Agent use, ordinary tests/checks, or a project-specific workflow, and
  name affected workflow/adoption impact, observable success criteria,
  non-goals, evidence, and compatibility risk.
- Reproduction steps and proposal examples should use placeholder-safe command shapes such as `<project-dir>`, `<Loopora checkout>`, or `<redacted>` instead
  of real local paths.
- When a report or proposal depends on first-use, Web, readiness, package identity, or environment behavior, include the public readiness report status
  and paste the public issue support bundle first. Paste public doctor/version
  output only when the template or maintainer asks for lower-level evidence;
  never paste command lines. Use `loopora version --json` only when structured
  identity is requested.
- Security-sensitive reports must follow [SECURITY.md](SECURITY.md) instead of
  public issues.

## Community Standards

Public issues, pull requests, and reviews follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Keep collaboration respectful, safe, and evidence-oriented; do not publish secrets, exploit details, private logs, local paths, or sensitive run artifacts in public channels.

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
- Select the PR template change type so maintainers can triage bug fixes, user-visible behavior, docs/support work, refactors, and release/security/distribution-sensitive changes differently.
- Add or update tests for behavior changes.
- Run the focused tests for the touched area plus the fast gates above.
- Paste the final `### Loopora PR Evidence` block from `uv run loopora dev check --pr-evidence`; it is the main local evidence block for decision scope, public-safe evidence command source, recommended focused guide IDs, unmatched/ignored changed files, guide IDs run, skipped guide IDs, final default-fast result, and package-build cleanup.
- Use `uv run loopora dev check --list --pr-evidence` while planning, or pass explicit paths with `--changed-file <path>` or trailing path arguments when Git detection is unavailable or a script already knows the diff.
- Add separate notes only for unmatched stable-boundary files that needed additional focused, journey, review, or probe evidence, and for any recommended or boundary-relevant guide IDs skipped with a reason.
- In public PR evidence, paste the public issue support bundle first as redacted diagnostic output when readiness or environment evidence matters. Paste public doctor/version output only when lower-level evidence or identity is requested, using `loopora version --json` only when structured identity is requested, not local command lines; use placeholders such as `<project-dir>`, `<Loopora checkout>`, or `<redacted>` for any command/path examples.

## Project Governance

Read [GOVERNANCE.md](GOVERNANCE.md) before proposing changes that affect maintainer-owned decisions such as supported release tags, package distribution, security posture, compatibility/migration risk, or license status. This repository currently does not declare a license. Do not add license metadata, copy third-party code, or change distribution terms without explicit maintainer approval.
