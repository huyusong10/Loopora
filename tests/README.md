# Loopora Verification Map

Loopora verifies stable behavior with the smallest evidence set that can reliably decide whether a contract still holds.

## Verification Types

| Type | Directory | Purpose |
| --- | --- | --- |
| Contract checks | `tests/checks/contracts/` | Deterministic public behavior, schemas, CLI/API boundaries, security, and package policy |
| Journey checks | `tests/checks/journeys/` | Current user-visible Web flows, browser behavior, and responsive layout |
| Real probes | `tests/probes/real_environment/` | Opt-in checks against real provider CLIs, Agent hosts, or a foreground Web process |
| Reviews | `tests/reviews/` | Visual or semantic evidence that needs human or Agent judgment |
| Scenarios | `tests/scenarios/` | Manual exploratory paths that are not stable machine assertions |
| Experiments | `tests/experiments/` | High-cost research tasks that do not block ordinary development |

## Default-Fast Gate

Run this before committing ordinary changes:

```bash
uv run loopora dev check
```

Inspect its exact steps without running them:

```bash
uv run loopora dev check --list
```

The gate checks locked dependencies, dependency compatibility, JavaScript syntax, Python static rules, the accepted repository complexity budget, whitespace, wheel/sdist contents, and contract tests. The package step removes `tmp/package-check` and generated `src/loopora.egg-info` after either success or failure.

For a touched stable boundary, run the nearest contract test directly. For Web routes, templates, navigation, forms, or browser state, also run:

```bash
uv run pytest -q tests/checks/journeys
```

Tests should assert public return values, stable IDs, status and error semantics, persisted artifacts, accessible controls, and user-observable results. Do not lock private helper names, CSS classes, DOM nesting, transient call order, or exact prose unless they are the contract.

## Opt-In Evidence

Read the real-probe playbook before using a live host:

```bash
python tests/probes/real_environment/run_real_probes.py --show-playbook
```

Common release-oriented suites are `release`, `real-agent`, `real-cli`, and `release-web`. They may skip when their explicit environment switch or host command is unavailable.

Visual and expression reviews are intentionally separate from deterministic checks:

```bash
uv run python tests/reviews/run.py --case rendered-surfaces
```

Real workflow experiments require explicit opt-in:

```bash
LOOPORA_ENABLE_REAL_WORKFLOW_EXPERIMENTS=1 uv run pytest -q tests/experiments/real_workflows
```

Prefer one high-value behavior test over many implementation-branch mirrors. A deleted feature should lose its obsolete assertions and gain concise evidence for the remaining public path.
