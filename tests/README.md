# Loopora Verification Map

Loopora verification is organized by two independent questions:

- Verification type: what kind of evidence proves the behavior?
- Run profile: when should that evidence be collected?

Older labels such as L1/L2/L3 are no longer the primary taxonomy. They mixed execution cost with evidence meaning and did not describe review-only or experiment-style cases well.

## Verification Types

| Type | Directory | What It Proves | Result Shape |
| --- | --- | --- | --- |
| Contract Checks | `tests/checks/contracts/` | Stable public contracts, data semantics, schema behavior, CLI/API boundaries, static asset contracts | Deterministic pytest pass/fail |
| Journey Checks | `tests/checks/journeys/` | User-visible local flows that need browser, templates, client state, or in-process Web behavior | Deterministic pytest pass/fail plus local artifacts when useful |
| Real Probes | `tests/probes/real_environment/` | Real provider CLIs, real Agent hosts, or a real `loopora serve` process still satisfy the minimal external-boundary contract | Opt-in pytest pass/fail plus phase reports |
| Review Cases | `tests/reviews/` | Fuzzy visual, semantic, expression, and experience quality that code can help capture but should not pretend to judge alone | Screenshots, reports, machine hints, human/agent review |
| Scenarios | `tests/scenarios/` | Manual exploratory journeys through stable product goals | Playbook steps and evidence boundaries |
| Experiments | `tests/experiments/` | High-cost or research-like real workflows that preserve evidence but are not default gates | Opt-in artifacts and analysis |

## Run Profiles

| Profile | When | Typical Entry |
| --- | --- | --- |
| `default-fast` | Every normal code change before commit | Dependency compatibility, static JS syntax, Ruff, whitespace-safe diff, package build, and contract checks |
| `focused` | A touched module has a nearby contract or journey check | Focused pytest path under `tests/checks/contracts/` or `tests/checks/journeys/` |
| `journey` | A touched UI flow, CI container job, or release profile needs rendered/user-flow evidence | `uv run pytest -q tests/checks/journeys` |
| `opt-in` | A user/reviewer asks for visual, semantic, real-host, or exploratory evidence | `tests/reviews/run.py`, `tests/probes/real_environment/run_real_probes.py`, or a scenario playbook |
| `release` | Before shipping changes that depend on real external hosts or browser/server integration | Real probe suites plus relevant journey checks |
| `experiment` | The goal is to learn from a realistic task, not to block ordinary development | Explicit experiment tests under `tests/experiments/` |

## Default-Fast Gate

For ordinary code work, run:

```bash
uv run loopora dev check
```

`loopora dev check --list` prints the expanded default-fast steps, changed-file detection status, focused selector choices, the focused check guide, recommended focused checks, and changed files that do not match any focused guide for the current Git changes, including non-ignored untracked files, without running them. Add `--pr-evidence` to print a template-ready `### Loopora PR Evidence` Markdown block instead of the full plain guide; JSON callers receive the same block under `pr_evidence_summary.template_markdown` with an explicit `evidence_stage` and changed-file detection line. Use `--focused-ran recommended` or explicit guide IDs on remaining focused or final evidence commands to record focused checks that already passed; decision-stage `--list --pr-evidence` notes those values but still does not count them as run evidence. When Git detection is unavailable or a script already knows the changed paths, pass repeated `--changed-file <path>` options or trailing changed-path arguments to drive the same recommendations from explicit paths instead of Git; values may be workdir-relative paths or absolute paths under `--workdir`, and reports normalize them to project-relative paths. Paths outside `--workdir` or parent-relative paths are ignored changed files and are reported separately instead of driving recommendations. When changed files exist and no provided inputs were ignored, plain output says `ignored changed files: none`; when all changed files match focused guides, it says `unmatched changed files: none`, so PR evidence can record both states directly. Plain output also prints a `PR evidence:` reminder before the command list. `loopora dev check --help` and `--list` expose the current selectors: `recommended`, `all`, and guide IDs. When recommendations exist, run them directly with:

```bash
uv run loopora dev check --focused recommended
```

Use `uv run loopora dev check --list` as the authoritative source for the current executable default-fast commands. The gate covers dependency lock dry-run, dependency compatibility, static JavaScript syntax, Ruff, whitespace-safe diff, package build, and contract checks.

Run package-build through `loopora dev check` instead of copying a hand-rolled build sequence. The package-build step removes stale `tmp/package-check` output and generated `src/loopora.egg-info` metadata before build, opens the generated wheel and sdist to verify Web templates/static assets, Agent/Alignment prompt assets, logo assets, source package manifest, public README documents, public design documents, public diagram assets, the `loopora` console script entry point, the `python -m loopora` module entry, public project URLs, contributor/maintainer identity metadata, public discovery keywords/classifiers, Python requirement metadata, runtime dependency metadata, and the current no-license-declared boundary, then removes package output and generated metadata after pass or fail.

## Focused Check Guide

Use the focused guide when a pull request touches a stable boundary and needs local evidence before the full default-fast gate. `loopora dev check --list` recommends focused checks from the current changed paths, separately lists changed files that did not match a focused guide or reports `none` when every changed path matched, reports ignored changed files separately, and prints the current expanded pytest commands. Use repeated `--changed-file <path>` options or trailing changed-path arguments with `--list` or `--focused recommended` when the relevant changed paths come from a script, patch, or non-Git workspace. `loopora dev check --focused recommended` runs the recommended guides and, after they pass, points to the final `--pr-evidence --focused-ran ...` command for the same evidence scope. Partial explicit focused passes point to remaining recommended guide IDs and carry already-passed guide IDs forward with `--focused-ran`. Use `--focused <guide-id>` or comma-separated guide IDs when the stable boundary is broader than the changed-file match:

| Guide ID | Boundary | Typical command |
| --- | --- | --- |
| `first_use_readiness` | First-use readiness and local recovery | `uv run loopora dev check --focused first_use_readiness` |
| `web_surfaces` | Web routes, templates, and static assets | `uv run loopora dev check --focused web_surfaces` |
| `agent_native` | Agent Native plan/run surfaces | `uv run loopora dev check --focused agent_native` |
| `alignment_bundle` | Alignment and bundle compiler behavior | `uv run loopora dev check --focused alignment_bundle` |
| `core_execution` | Core execution, context, and provider boundaries | `uv run loopora dev check --focused core_execution` |
| `runtime_state` | Run lifecycle and local runtime state | `uv run loopora dev check --focused runtime_state` |
| `open_source_collaboration` | Open-source collaboration, review/scenario evidence workflows, and distribution | `uv run loopora dev check --focused open_source_collaboration` |

For pull request evidence, paste the final `### Loopora PR Evidence` block from `loopora dev check --pr-evidence`; it is the main local evidence block for decision scope, public-safe evidence command source, focused guide recommendations, unmatched/ignored changed files, guide IDs run, skipped guide IDs, final default-fast result, and package-build cleanup. Add separate notes only for unmatched stable-boundary files that needed additional focused, journey, review, or probe evidence, and for any boundary-relevant guide IDs you skipped with a reason.

Use narrower pytest paths when the touched behavior has a clear local boundary. Journey checks move out of the local default-fast gate: run them when the touched change affects rendered pages, browser state, navigation, forms, or the CI/release profile asks for them. Contract and journey checks should assert user-observable behavior, public return values, stable IDs, status semantics, structured errors, persisted artifacts, and accessible controls. They should not assert private variables, CSS classes, DOM nesting, transient implementation order, or exact copy unless the copy is itself the contract.

## Real Probes

Real probes are handbook-first. Before running or interpreting them, read:

```bash
python tests/probes/real_environment/run_real_probes.py --show-playbook
```

Common entries:

```bash
python tests/probes/real_environment/run_real_probes.py --suite release
python tests/probes/real_environment/run_real_probes.py --suite real-agent --agent-targets codex,claude,opencode
python tests/probes/real_environment/run_real_probes.py --suite real-cli --cli-targets codex,claude,opencode
python tests/probes/real_environment/run_real_probes.py --suite release-web
```

The GitHub manual Real Probe workflow is only a wrapper around this runner. Its `release` suite selects `real-agent`, `real-cli`, and `release-web`; real workflow experiments remain opt-in through the experiment gate below and are not mixed into the release probe by default.

Real probes may skip on ordinary developer machines, but the skip reason must name the missing environment switch or command template. Phase reports are written under `.loopora/real-probes/` so a failing run exposes process, model, artifact, state, and command evidence without forcing the operator to infer progress from quiet stdout. The GitHub workflow uploads those reports as `loopora-real-probe-reports` even when the probe job fails or skips.

Real probes use the current model and reasoning configuration in the real host CLI by default. They should not pass `--model`, `--effort`, `--variant`, or provider model env vars on the ordinary release path. Set `LOOPORA_REAL_PROBE_ALLOW_MODEL_OVERRIDE=1` only when the release deliberately validates an explicit external configuration override.

## Review Cases

Review cases are separate from deterministic checks. They are case-first and intentionally allow fuzzy semantic checks such as text crowding, arrows crossing labels, clipped controls, expert-language leakage, misleading diagrams, or page chrome compressing content.

Run:

```bash
uv run python tests/reviews/run.py --case rendered-surfaces
uv run python tests/reviews/run.py --case rendered-surfaces --url home=http://127.0.0.1:8000/
```

SVG diagrams and Web pages share the same review runner and case format. Logo assets are not review-case targets; they keep ordinary structural checks for parseability, serving, and references.

## Experiments

Real workflow experiments are explicitly opt-in:

```bash
LOOPORA_ENABLE_REAL_WORKFLOW_EXPERIMENTS=1 uv run pytest -q tests/experiments/real_workflows
```

Experiments may preserve copied workspaces, run artifacts, proof output, and review notes. They should not become release blockers unless the shipped feature is specifically about that workflow.

## Guardrails

- Use deterministic code checks for stable contracts.
- Use review cases when code can collect pixels/text/hints but final judgment is semantic.
- Keep expression-flexibility examples in review cases instead of multiplying contract checks for every acceptable wording.
- Use scenarios when the useful artifact is an exploratory route rather than an automated assertion.
- Use experiments when the task is costly, provider-dependent, or intentionally research-like.
- Prefer one high-value journey over many branch-mirror tests.
- Keep language-specific checks narrow and focused on locale selection or resource presence, not exact phrasing.
- Keep legacy compatibility coverage separate from new-path quality assertions.
