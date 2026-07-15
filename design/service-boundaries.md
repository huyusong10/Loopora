# Loopora Service Boundaries

The implementation follows dependency direction, not filename prefixes. Higher layers may depend on lower layers; lower layers do not import CLI, Web, local host adapters, or presentation code.

## Dependency Direction

| Layer | Responsibility | May depend on | Must not depend on |
| --- | --- | --- | --- |
| Kernel | Loop/Run identity, steps, evidence, coverage, verdict, domain events, replay invariants | standard library and stable value types | services, DB adapters, CLI, Web, provider clients |
| Compiler | Reviewed judgment, bundle/schema normalization, strategy and role compilation | Kernel types and pure validation | CLI/Web request objects, local process state |
| Application services | Use cases, transactions, persistence coordination, recovery decisions | Kernel, compiler, repositories, explicit ports | terminal rendering, HTML templates, browser state |
| Adapters | CLI, Web, Agent Native, DB/filesystem repositories | application services and public projections | reimplementing compiler, evidence, or verdict rules |
| Integrations | provider commands, host detection, workers, real probes | explicit service ports and runtime contracts | deciding task proof or product fit |

Cycles across these layers are defects. Compatibility facades may re-export stable public names but internal callers use the owning implementation directly.

## Ownership Map

| Boundary | Owner | Notes |
| --- | --- | --- |
| Domain values and invariants | `loopora.kernel`, `loopora.events` | Pure and replayable; no surface imports. |
| Run orchestration | RunEngine and runner services | Writes through event transactions and returns public projections. |
| Bundle/schema | bundle/compiler modules; `loopora.bundles` is the compatibility facade | One normalization path for Web, CLI, import/export, and Agent Native. |
| Strategy/roles | Strategy Source and role-definition modules | Generic composition; task variation is data. |
| Alignment | alignment application service plus generic task compiler | Conversation gathers judgment; compiler projects it without domain routing. |
| Persistence | DB repositories and file IO services | Atomic writes, scoped paths, explicit transactions. |
| Agent Native | agent adapter and native service modules | Host remains executor; Loopora validates dispatch and submissions. |
| CLI | command registration plus thin presenters | No business decisions; JSON projects service results. |
| Web | route groups, request parsing, templates/static assets | Routes remain thin and share services with CLI. |
| Diagnostics/recovery | readiness, archive/reset, redaction services | Read-only checks do not mutate; destructive actions require explicit confirmation. |
| Provider execution | executor and process-stream adapters | Normalizes provider results into runtime contracts. |

## Boundary Rules

- A service module exists for a cohesive use case, not for each output field, error branch, language, or task example.
- Prefer one module of 150-400 cohesive lines to five mutually dependent modules with one helper each.
- Data catalogs use validated assets only when operators or localization need to edit data independently. Moving Python branching into a giant generated asset is not simplification.
- CLI and Web may have separate renderers, but action readiness and error semantics originate in a shared service projection.
- Public facades are documented explicitly. Other `loopora.*` modules are private during the experimental phase.
- Tests may assert layer direction and public facades; they do not assert a private helper's filename or that a large module was split into a particular inventory.
- New modules spend the repository budget in `complexity-budget.md`; a new module normally replaces or consolidates an existing one.

## Validation Entry Points

- `uv run ruff check src/loopora tests scripts`
- focused checks selected by the touched stable boundary
- `uv run loopora dev check` for the default-fast gate
- `uv run python scripts/complexity_budget.py --enforce` once the accepted reduction target is reached

When design and implementation conflict, first decide whether the stable product contract changed. Private module placement follows the implementation and complexity budget; it is not promoted to a contract to make a structural test pass.
