# Loopora Complexity Budget

Status: Accepted on 2026-07-15.

Loopora should preserve one stable product loop—`compose -> review -> run -> collect evidence -> verdict`—with the smallest maintainable set of concepts, modules, commands, dependencies, and verification assets. A local split is not an improvement when repository-wide navigation, coupling, test cost, or user choice increases.

## Research Basis

The comparison uses current upstream source snapshots and one repeatable measurement method: count physical Python files and lines under the principal runtime package, then derive modules per KLOC and root-package file count. These are directional comparisons, not rankings: each project has different provider, compatibility, and deployment scope.

| Project snapshot | Relevant design signal | Runtime files / lines | Modules per KLOC | Root modules | Loopora takeaway |
| --- | --- | ---: | ---: | ---: | --- |
| [OpenAI Agents SDK `4d9677850cb3`](https://github.com/openai/openai-agents-python/tree/4d9677850cb3) | `Agent` and `Runner` are the primary primitives; tools, handoffs, guardrails, and sessions extend them. | 289 / 95,871 | 3.01 | 37 | Keep a small public core even when integrations grow. |
| [smolagents `e3a5b8994b30`](https://github.com/huggingface/smolagents/tree/e3a5b8994b30) | The project explicitly presents itself as barebones and centers two agent modes on one multi-step loop. | 18 / 12,774 | 1.41 | 18 | Prefer generic execution mechanics over task-domain class or module taxonomies. |
| [LangGraph core `b96f6170e7ed`](https://github.com/langchain-ai/langgraph/tree/b96f6170e7ed/libs/langgraph/langgraph) | The core stays a low-level stateful orchestration layer; higher-level agent behavior is a separate layer. | 78 / 27,846 | 2.80 | 9 | Separate durable workflow mechanics from optional product guidance. |
| [Pydantic AI slim `6a337927891f`](https://github.com/pydantic/pydantic-ai/tree/6a337927891f/pydantic_ai_slim/pydantic_ai) | Type-safe composable capabilities carry variation without a module per use case. | 240 / 83,398 | 2.88 | 42 | Encode variation as typed data/composition before adding dispatch modules. |
| Loopora `069cb4abe057` | One product package currently carries runtime, Web, CLI, alignment, recovery, domain catalogs, and verification support. | 1,055 / 127,140 | 8.30 | 963 | The repository is over-fragmented even after accounting for broader product scope. |

The architectural lessons are also supported by the projects' own descriptions: [OpenAI Agents SDK agents](https://openai.github.io/openai-agents-python/agents/) makes Agent the core building block; [LangGraph](https://github.com/langchain-ai/langgraph) identifies itself as low-level orchestration for durable, stateful agents; [smolagents](https://github.com/huggingface/smolagents) deliberately describes a barebones library; and [AutoGen](https://github.com/microsoft/autogen) documents a layered Core / AgentChat / Extensions split and a ground-up rewrite after earlier design lessons.

## Baseline

Measured from a clean `069cb4abe057` checkout on 2026-07-15:

| Dimension | Baseline evidence |
| --- | ---: |
| Production Python | 1,055 files; 127,140 physical lines; median 108 lines |
| Fragmentation | 415 files at or below 80 lines (39.3%); 143 import/data-only modules (13.6%) |
| Namespace | 963 Python files directly under `src/loopora` |
| User surface | 14 visible root commands; 42-line root help at 120 columns; 7 required runtime dependencies |
| Contract evidence | 746 Python files / 123,371 lines; 650 `test_*.py` files |
| Structural-mirror evidence | 287 files and 67,753 lines inspect source/design shape; 54.9% of contract-test lines |
| Default contract feedback | 3,013 tests passed in 242.80 seconds; 243.49 seconds wall time |
| Design assets | 1,766 lines across the mapped design documents |
| Onboarding docs | 1,033 lines across English and Chinese README files |
| Distributed source payload | 8.64 MiB under `src/loopora`, excluding bytecode caches |

History is part of the evidence: the latest commit increased production Python files from 640 to 1,055 (+64.8%) while contract Python files moved only from 742 to 746. The largest new families were `executor_alignment_*`, `alignment_traceability_*`, and narrow CLI/recovery projections. This budget therefore prioritizes undoing one-function/one-catalog-module fragmentation and implementation-mirror tests before micro-optimizing individual functions.

## Required Budgets

The target column is the acceptance boundary for the current simplification initiative. Until every target is met, each merged slice must ratchet every touched metric downward and may not worsen an untouched metric. Once met, the targets become hard caps in the default-fast gate.

| ID | Metric | Target | Why this protects the product |
| --- | --- | ---: | --- |
| S1 | Production Python files | <= 600 | Restores navigability and removes the module-per-branch pattern. |
| S2 | Production physical lines | <= 100,000 | Requires deletion or generalization, not file concatenation alone. |
| S3 | Modules per KLOC | <= 6.0 | Prevents satisfying S1 by merely retaining large amounts of fragmented code. The external reference range is 1.41-3.01; 6.0 is an interim allowance for Loopora's CLI and Web surfaces. |
| S4 | Root-package Python files | <= 450 | Makes stable subsystem ownership discoverable without searching a flat thousand-file namespace. Moving files without clarifying dependency direction does not count. |
| S5 | Files at or below 80 lines | <= 25% | Discourages import-only facades and one-function files while allowing small types and entry points. |
| S6 | Import/data-only modules | <= 8% | Keeps compatibility and catalogs exceptional rather than the dominant architecture. |
| D1 | Runtime import cycles | 0 | Preserves one-way subsystem reasoning and safe deletion. |
| U1 | Visible root CLI commands | <= 8 | A first-time user should choose a route, not understand the internal resource model. Compatibility aliases may remain hidden during the experimental transition. |
| U2 | Root help physical lines at 120 columns | <= 32 | Keeps the first screen actionable and moves detail behind contextual help. |
| U3 | Required runtime dependencies | <= 7 | Prevents feature growth from silently increasing installation and security surface. |
| E1 | Contract Python files | <= 400 | Evidence should be grouped by stable behavior rather than implementation branch or module. |
| E2 | Contract-test physical lines | <= 80,000 | Forces removal of duplicated fixtures, exact-copy assertions, and source-layout mirrors. |
| E3 | Structural-mirror share of contract lines | <= 15% | Default evidence should prove public behavior; source/design inspection is reserved for a few dependency and packaging invariants. |
| E4 | Warm contract-check wall time on the same reference machine | <= 120 seconds | Keeps ordinary refactoring feedback fast enough to use continuously. Timing is reported, not treated as deterministic across unlike machines. |
| A1 | Mapped design lines | <= 900 | Design is a boundary map, not a second implementation. |
| A2 | Paired README lines | <= 600 | The adoption path must be understandable without reading an operator handbook. |
| P1 | Distributed source payload | <= 8 MiB | Bounds generated fixtures, duplicated prose, and packaged catalogs that affect every installation. |

Ruff remains the function-level complexity gate. Repository budgets complement it: a thousand individually lint-clean modules can still be an unmaintainable system.

## Accepted Result

Measured after the reduction on 2026-07-15. The contract gate retained 829 behavior checks and completed in 24.61 seconds on the reference machine.

| Dimension | Baseline | Accepted result | Change |
| --- | ---: | ---: | ---: |
| Production Python | 1,055 files / 127,140 lines | 413 files / 72,089 lines | -60.9% files / -43.3% lines |
| Fragmentation | 39.3% thin / 13.6% import-data-only | 24.7% thin / 5.3% import-data-only | both within budget |
| Namespace and coupling | 963 root modules / unmeasured cycles | 321 root modules / 0 cycles | -66.7% root modules |
| User surface | 14 commands / 42 help lines | 8 commands / 28 help lines | -42.9% / -33.3% |
| Contract evidence | 746 files / 123,371 lines | 305 files / 26,144 lines | -59.1% files / -78.8% lines |
| Structural mirrors | 67,753 lines / 54.9% | 1,110 lines / 4.2% | -98.4% lines |
| Default contract feedback | 3,013 checks / 243.49s wall | 829 checks / 24.94s wall | -89.8% wall time |
| Design / onboarding / source | 1,766 / 1,033 lines / 8.64 MiB | 294 / 590 lines / 4.33 MiB | -83.4% / -42.9% / -49.9% |

The smaller test count reflects deletion of private source-layout mirrors and retired feature assertions. Stable evidence, verdict, lifecycle, local-data, path-containment, error-redaction, package-build, and first-use behavior remain in the default-fast gate.

## Anti-Gaming Rules

- A metric is not improved by moving production behavior into tests, assets, generated files, or a single oversized module.
- Domain examples belong in documentation, review cases, or data fixtures unless they change a stable compiler rule. A new task domain must reuse the generic judgment schema before it may add executable routing code.
- Compatibility facades need an identified external consumer or documented migration window. Internal imports must use the owning module directly.
- Structural tests may protect package contents, public exports, dependency direction, or security-sensitive ownership. They must not require a particular private filename, helper location, split count, or prose layout.
- User-visible aliases may remain during the experimental transition, but only primary routes appear on the root help screen.
- Deleting tests is valid only when another stable behavior proof remains or the deleted assertion was an implementation mirror. Test count reduction alone is not evidence of preserved behavior.
- Every simplification slice records before/after metrics and runs focused behavior checks. Completion requires the full default-fast gate and a fresh complexity report.

## Measurement And Failure Meaning

The repository complexity checker owns the deterministic counts and prints both baseline deltas and target status. A target failure means the simplification initiative is incomplete; a post-acceptance regression means a proposed change is spending complexity budget and needs either a compensating deletion or an explicit design change.

Timing variance, fuzzy UX quality, and real-provider behavior remain review/probe evidence. They must not be converted into brittle hard assertions merely to make the budget machine-readable.
