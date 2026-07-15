# Loopora Contracts

Loopora has one product responsibility: turn reviewed task judgment into a runnable Loop, preserve evidence across rounds, and issue a verdict that distinguishes task proof from process completion.

The stable user flow is:

`choose route -> review judgment -> compile Loop -> run steps -> collect evidence -> issue verdict -> continue or close`

This document records externally meaningful behavior. Private filenames, helper placement, prompt wording, CSS/DOM shape, and task-domain examples are not contracts.

## Stable Boundary Map

| Boundary | Stable claim | Owning surface | Primary evidence | Not a contract |
| --- | --- | --- | --- | --- |
| Product fit | Loopora is for multi-round work whose risk cannot be judged by one Agent pass or one hard check. Fit remains a human decision, not an automatic classifier. | project documentation and reviewed Plan File | first-use and plan-validation behavior checks | Exact explanation copy or example task list |
| First-use route | A new user can install a same-Agent entry, inspect readiness, or open the local Web surface without needing to understand the internal resource model. Read-only diagnostics do not mutate the target project. | `init`, `doctor`, `serve` | first-use behavior checks | Every diagnostic on the root help screen |
| Reviewed judgment | Runnable work carries task scope, success, fake-done risk, evidence preference, execution strategy, residual-risk policy, tradeoffs, and role/workflow posture. Missing required judgment blocks READY. | Alignment service and bundle compiler | alignment validation and READY lifecycle checks | A regex taxonomy of business domains |
| Generic compilation | The compiler projects reviewed judgment into spec, role posture, handoffs, evidence queries, and GateKeeper strictness through one generic workflow shape. | Alignment compiler, bundle normalization | generic task-anchor and bundle semantic checks | A dedicated workflow, role set, or Python module for each task domain |
| Task anchoring | The original task remains visible in the working agreement and runnable bundle. Validation rejects a candidate that loses the task anchor. | Alignment traceability and candidate validation | task-anchor traceability checks | Exact keyword extraction or prose order |
| Loop plan format | A Plan File is parseable YAML with stable schema/version, spec, roles, workflow, execution settings, and control fields. Normalization is shared by Web, CLI, and Agent Native paths. | Bundle compiler and normalization | schema/semantic/YAML contract checks | Field order, comments, or private normalized intermediates |
| Workflow model | The default workflow is linear and explainable. Steps may read explicit handoffs/evidence; GateKeeper owns `finish_run`. Optional expert controls cannot bypass validation. | Strategy Source and workflow normalization | workflow policy and identifier checks | One preset per business use case |
| Role model | Builder changes the target; Inspectors challenge claims; GateKeeper judges closure. Optional expert roles are reviewed workflow data, not mandatory built-ins. Names and prose may be localized while stable archetype IDs remain language-neutral. | Role definitions and prompt assets | role schema and locale checks | Exact role display names or prompt sentences |
| Evidence model | Evidence has stable identity, source, artifact refs, target links, and semantic status. Evidence count alone never proves progress. | Kernel evidence and coverage | event/store/coverage contract checks | Private projection cache shape |
| Verdict model | Run lifecycle and task verdict are separate. Process success cannot pass the task; missing required evidence, blocking gaps, or unmanaged residual risk prevents closure. | Kernel verdict and RunEngine | verdict, coverage, and closure causation checks | A presenter-specific summary payload |
| Event causation | Step claims, instructions, submissions, accepted evidence, coverage recomputation, verdicts, and closure are causally linked and written atomically where partial state would be unsafe. | Kernel event store and RunEngine | transaction, replay, and invariant checks | Internal function call order |
| Continuation | An unresolved run carries bounded gaps into the next run; regression repairs first; contract change returns to review; a recorded passing result stays closed unless advisory follow-up is explicit. | Run continuation service | rerun/continuation behavior checks | Evidence volume as progress |
| Agent Native | The current Coding Agent remains the execution subject. Loopora owns review, role dispatch instructions, evidence acceptance, lifecycle recovery, and verdict projection; it does not silently take over the host session. | Agent adapters and Agent Native service | plan/run/next/submit focused checks | Nested provider execution or implicit subagent fan-out |
| Headless execution | Headless runners obey the same StepInstruction, evidence, coverage, and verdict contracts as Agent Native execution. | Runner service | core execution and runtime-state checks | Provider-specific transcript formatting |
| Web/CLI parity | Web and CLI may present differently but share service decisions, stable status/action IDs, validation, readiness, and recovery semantics. JSON is the automation surface. | Web routes, CLI presenters, services | API/CLI behavior checks | Exact human copy or layout |
| Local-first state | State and artifacts remain local by default. Project scope, path containment, atomic replacement, and explicit destructive confirmation protect local data. | DB, file IO, recovery services | path, archive, reset, and file-write checks | Local absolute paths as public fields |
| Web security | Loopback is the default. Non-loopback serving fails closed without authentication or explicit unsafe opt-in; public diagnostic output redacts secrets and local paths. | Web auth, URL safety, diagnostics redaction | network/auth/redaction checks | Token values or browser layout |
| Experimental compatibility | v3 local state is a development reset boundary. Public facades and CLI aliases may provide bounded compatibility, but private root modules are not public APIs merely because they are importable. | documented facades and CLI entry | schema/reset/public entry checks | Indefinite preservation of private helper modules |
| Distribution | Wheel and sdist contain required runtime templates, static files, prompt assets, provenance, public docs, and entry points; generated build output is cleaned. | package metadata/build check | package-build gate | Checkout-local paths or stale generated metadata |
| Open-source support | Security, contribution, issue, and release routes remain explicit in repository documentation. Public access does not imply a license while no license is declared. | repository documentation | open-source collaboration checks | Guaranteed support response time |

## Product Rules

### One generic compiler

Task-specific judgment belongs in the reviewed agreement and resulting data, not in a built-in business-domain router. A payments task and a data migration task may produce different role posture or evidence text because the user reviewed different judgment, but Loopora does not infer a permanent workflow taxonomy from keywords.

Examples and fixtures may teach the alignment Agent how to ask better questions. They must not become hidden executable dispatch tables. A new task example should normally require no production Python module and no new contract-test family.

### Evidence before closure

The following invariants fail closed:

- required evidence targets are missing, weak, or blocked;
- a GateKeeper pass has no supporting accepted evidence;
- a lifecycle failure is presented as a task result;
- residual risk lacks explicit ownership or acceptance policy;
- a continuation claims progress only because evidence count increased;
- local governance was required by the target project but skipped.

### Stable semantics, flexible expression

Stable IDs, schemas, action kinds, error meanings, accessible names, and path/security boundaries may be asserted exactly. Human prose, localization choices, prompt wording, CSS classes, DOM nesting, and private module layout remain flexible.

## Verification Map

| Claim family | Default proof | Additional evidence when touched |
| --- | --- | --- |
| Bundle/schema/compiler | deterministic contract checks | representative Web or Agent Native flow |
| Kernel/events/evidence/verdict | deterministic invariant and replay checks | focused runtime integration |
| CLI/API status and recovery | public return/status/action checks | first-use or runtime focused guide |
| Web navigation/forms/security | route/API checks | browser journey for user-visible flow |
| Provider/host boundary | local adapter contract | opt-in real probe |
| Visual/expression quality | structural accessibility checks | review artifact, not brittle copy assertion |
| Packaging/open-source metadata | default package build and doc checks | release evidence when shipping |

A failing behavior check means the stable claim regressed or intentionally changed. A source-layout test that fails only because a private helper moved is evidence debt and should be removed, not used to restore accidental architecture.
