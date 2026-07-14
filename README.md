[简体中文](./README.zh-CN.md) | **English**

<p align="center">
  <img src="./src/loopora/assets/logo/logo-with-text-horizontal.svg" alt="Loopora" width="720" />
</p>

<p align="center">
  <a href="https://www.python.org/">
    <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white">
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img alt="FastAPI" src="https://img.shields.io/badge/web-FastAPI-009688?logo=fastapi&logoColor=white">
  </a>
  <a href="https://github.com/huyusong10/Loopora/actions/workflows/ci.yml?query=branch%3Adev">
    <img alt="CI" src="https://github.com/huyusong10/Loopora/actions/workflows/ci.yml/badge.svg?branch=dev">
  </a>
  <a href="https://github.com/huyusong10/Loopora/actions/workflows/codeql.yml?query=branch%3Adev">
    <img alt="CodeQL" src="https://github.com/huyusong10/Loopora/actions/workflows/codeql.yml/badge.svg?branch=dev">
  </a>
  <img alt="Agent native" src="https://img.shields.io/badge/agent--native-loop-2563EB">
  <img alt="Local first" src="https://img.shields.io/badge/local--first-evidence-0D7C66">
  <img alt="Status" src="https://img.shields.io/badge/status-experimental-D66A36">
</p>

# Loopora

**Turn `/goal`-style long tasks into Human-shaped Loops with evidence and verdicts.**

In Coding Agents, persistent-goal mechanisms like `/goal` feel natural: give the Agent an objective, it remembers it, keeps pursuing across turns. This works for clear goals, fast feedback—"fix this error," "keep cleaning this module," "get this test suite green."

The hard part of complex tasks isn't just "keep the Agent going." It's judging after each round: did it actually do the right thing? Is evidence sufficient? Is risk acceptable? Should the next round pivot? Can this close now?

Real production feedback, incident feedback, business quality feedback often appears long after the task finishes. By the time final feedback arrives, early drift has already been reinforced by subsequent work. **Bare goals keep the task moving, but easily turn results into blind boxes**—the run looks more complete, but core risks might never have been proven.

Loopora solves this layer: when final feedback is too slow, errors cascade, and evidence needs intermediate governance, first choose the right route before setup or creation. When the task fits Loopora, use `/loopora-plan` to turn the fit reason, objective, completion criteria, fake-done patterns, evidence requirements, and blocking risks into a reviewable Loop plan. Then use `/loopora-run` to let the Agent execute continuously within that Loop.

Loopora reduces error accumulation, makes each round return to the same judgment, letting long tasks run more steadily and healthily.

Human-shaped Loop is not just the name of an essay. A candidate Loop cannot be only a task summary; each step should inherit these judgments, action boundaries, and evidence gaps.

To understand the philosophy behind this approach, read [Human-Shaped Loop](./HUMAN-SHAPED-LOOP.md).

<p align="center">
  <img src="./assets/diagrams/loopora-overview.en.svg" alt="Loopora turns human task judgment into a plan file, runs the Agent loop, and shows evidence and verdicts in Web" width="1000" />
</p>

## Project Status

Loopora is experimental local-first software. The current adoption path is a local source checkout: ordinary users install a wheel-backed copy with `uv tool install .`, while contributors may opt into an editable checkout. Each built wheel and sdist retains the reviewed checkout's build-time Git revision and clean/dirty state without local checkout paths, so different source snapshots remain distinguishable while the package version is fixed. `loopora --version` prints this compact package/source identity for issue reports; use `loopora version --json` when tooling needs the same path-free identity as structured data.

Public adoption notes:

- Support is best-effort through [SUPPORT.md](./SUPPORT.md), has no guaranteed response time, and follows the current development line plus release tags maintainers explicitly mark as supported.
- Run `loopora support` for the terminal-safe public reporting route. When readiness evidence is relevant, use `loopora support --workdir "$PWD" --public-issue-bundle` from a target project; it wraps the redacted `doctor --public-json` report with compact package/source identity and a human-readable readiness summary.
- In Web, open Support from top navigation or `/support` to copy the same workdir-scoped public issue support bundle; Same-Agent Setup embeds the same support panel when you are already there.
- Bare support output marks the report command preview-only and prints a target-project `loopora support --workdir "$PWD"` rerun command before the public issue bundle or public doctor command becomes ready. If the supplied target is missing or not a directory, the redacted report may still be useful evidence while setup target remains not ready.
- For custom Web targets, pass the same `--web-host` / `--web-port` flags to support before copying that command or opening the matching local-only Web Support URL.
- Diagnostic material: paste the public issue support bundle first when readiness or environment evidence matters. Use public doctor/version output only when a template or maintainer asks for the underlying report or identity. Keep `loopora support --json`, printed command lines, JSON command fields, and local Web Support URLs local-only.
- Vulnerabilities belong in [SECURITY.md](./SECURITY.md) or private reporting, not public issue details. If private reporting is unavailable, a public issue may only ask for a private channel.

This repository currently does not declare a license. Do not infer redistribution, reuse, or third-party intake rights from public repository access.

## Start Here

Before configuring an Agent or provider, run `uv run loopora demo --open` from this source checkout, or `loopora demo --open` after install. It executes a real three-iteration Loop through Loopora Core with a deterministic simulated executor, then opens a completed Run so you can inspect persisted evidence and the final verdict. The CLI and persistent Web banner also link a separate, initially empty creation playground where Fit and one-sentence Web composition do not inherit the sample Run's artifacts. Both projects share an isolated temporary App home; Demo resolves every target and symlink against that temporary root, removes arbitrary project switching, and fixes creation controls to the playground, so Ctrl-C can delete the entire Demo state without touching a real project. Add `--language zh` to keep terminal lifecycle and simulated checks, evidence, role handoffs, and verdict narrative in Chinese; stable identifiers remain language-neutral, while Web chrome still follows the browser locale. To continue with real work, stop Demo and use its copyable `loopora start --workdir "$PWD"` handoff from the target project; that command does not inherit the temporary Demo App home. Demo's passing verdict is product evaluation only, not proof of a real task or provider integration.

Use `loopora start --workdir "$PWD"` after install for a one-screen route chooser.

Before install:

- From a source checkout before install, run `uv run loopora start` while your shell is still in the Loopora checkout.
- From the target project, run `uv --directory <Loopora checkout> run loopora start --workdir "$PWD"`.
- Bare source-checkout output hides route commands, then prints a copyable `uv --directory <Loopora checkout> run loopora start --workdir "$PWD"` rerun command for the target project before you continue the review and route choice.

Route chooser behavior:

- With a concrete target but no completed fit review, plain `start` and `fit` expose a review-only Web Fit Guide command so the user can complete judgment interactively. Setup, creation, init, doctor, `/loopora-plan`, and run routes stay hidden or blocked; structured JSON keeps review actions separate from future route state.
- After a completed strong-fit review, start preflights the default local Web port and uses an available alternate in the route command when needed. If no alternate is found, it marks the Web route blocked until you choose a port.
- When the review is complete, start separates the routes: Web can continue independently. When exactly one current host is detected, the same-Agent path shows `init current` before the reviewed `/loopora-plan` message; unavailable or ambiguous detection shows explicit adapter choices instead. The message may be saved immediately, but it must not be pasted until setup reports ready.
- For automation, use `setup_gate_ready` and `setup_gate_blockers` to distinguish reviewed setup readiness from future route state. On the same-Agent action, `command_ready` describes the primary `init current` command, `action_ready` also accounts for applicable explicit choices, and `current_agent_host` carries only redacted detection state.
- It remains read-only: it does not install same-Agent project entries, start Web, or decide whether the task fits Loopora for you.

Pick the route before you install same-Agent project entries or create a Loop:

| Your situation | First action | Continue with |
| --- | --- | --- |
| Unsure whether this task needs Loopora | Run `loopora fit`, or `uv run loopora fit` from this checkout, before setup | Stop if direct Agent use, `/goal`, hard checks, or your existing project process can fully judge the task |
| Not inside an Agent session | Open the Fit Guide/Web choices route with `loopora serve --open --workdir "$PWD"` after install, or use the source-checkout command below before install from a target project | Use Fit Guide/Web choices for Web conversation, Plan File import, or manual expert mode; use same-Agent setup only from a current Codex, Claude Code, or OpenCode session |
| Already working inside Codex, Claude Code, or OpenCode | Run `loopora init current --workdir "$PWD"`; it installs the detected entry and confirms the `/loopora-plan` handoff in one command | Return to the same Agent session for `/loopora-plan`, review the READY preview, then run `/loopora-run` |
| Already have a plan file or exact contract/roles/flow | Use the Web import or manual expert path | Preview before creating or running the Loop |
| Inspecting an existing Loop or run | Open Web | Review evidence, verdict state, residual risk, and next action before continuing |

To carry one Run's review result outside the local Web UI, use `loopora loops export-run <run-id>` or the Run-detail **Export private evidence** action. The ZIP contains a curated contract/evidence/verdict snapshot with local absolute paths replaced; it omits workspace files, prompts, raw model output, provider transcripts, events, and logs. It still contains private task content, so review every file before sharing. It is not the public-safe support bundle, a project backup, a full transcript, or independent proof that the task passed. Use `--output <file.zip>` to choose a destination and `--force` only when replacement is intentional.

When a Loop has multiple Runs, Loop detail compares the latest two against stable coverage target IDs. It shows improved and regressed targets, closed and reopened gaps, and refuses a direct progress claim when the target contract changed or either Run lacks a comparable evidence baseline. A higher evidence count alone is not progress. Automation can read the same `run_progress` projection from `loopora loops status <loop-id>` or `GET /api/loops/<loop-id>`.

To return to existing work without remembering which resource command owns it, run `loopora status --workdir "$PWD"`. This project view is storage-read-only by default: it puts interrupted or active planning, Runs needing action, recent results, and saved Loops that have not run into one ordered next-step summary without changing stale records during observation. If a persisted Run or planning session still looks active after its local worker is gone, status reports the scoped candidates and prints an explicit `--reconcile` command; only that command moves those orphaned records into recoverable terminal states. A project-scoped reconcile does not touch another project and skips a live worker unless its planning record already carries a user cancellation request. Use `loopora status --all` only when you intentionally want a cross-project scan; use `--json` for the complete compact projection.

From a target project before installing, keep the source checkout anchored in copyable commands:

- Route chooser: `uv --directory <Loopora checkout> run loopora start --workdir "$PWD"`
- Web: `uv --directory <Loopora checkout> run loopora serve --open --workdir "$PWD"`
- Same-Agent path: `uv --directory <Loopora checkout> run loopora init current --workdir "$PWD"`; it includes the matching read-only readiness check. Use an explicit `<agent>` followed by doctor when host detection is unavailable or ambiguous.

## From `/goal` To Loop

If you would normally write:

```text
/goal port this React component library to Vue until it is deliverable
```

Loopora suggests splitting into two steps:

```text
/loopora-plan
```

Review the READY Loop preview, then:

```text
/loopora-run
```

The difference isn't command length—it's the reviewable judgment structure added before the long run starts.

| With bare `/goal` | With Loopora |
| --- | --- |
| Goal is usually one sentence | Goal becomes completion criteria, fake-done patterns, evidence requirements, and blocking risks |
| Agent mainly keeps pursuing the objective | Each round carries task judgment, action boundaries, evidence gaps, output requirements |
| Process can look increasingly complete | Each round must report proven, weak evidence, unproven, blocking items, residual risk |
| Closure easily relies on Agent declaring done | Task verdict needs supporting evidence; missing required evidence blocks pass |
| Human needs to repeatedly return to correct drift | Human reviews Loop before run, inspects evidence during run, intervenes at key points |

Loopora doesn't reject `/goal`. It inherits `/goal`'s core intuition: long tasks should keep moving. But for high-risk, multi-round, evidence-sensitive work, before continuing, first define "how will we judge it actually done."

## When Loopora Replaces `/goal`

Loopora does not fit every task. Use cases, agile iteration, and automated tests fit systems where feedback can be compressed enough: build a small slice, run a test, know immediately if it's right. Loopora fits slow-feedback systems: final feedback too late, errors cascade, "looks done" doesn't mean "actually done."

| Situation | Recommendation |
| --- | --- |
| Goal is small, one Agent pass plus one human review enough | Use Agent or `/goal` directly, no need for Loopora |
| Stable tests, evaluation suites, proof scripts, or automated proof can directly judge | Prefer those hard checks first |
| Final feedback fast, errors won't cascade | Use cases or direct Agent fit better |
| Task needs multi-round execution, each round creates new evidence | Loopora starts adding value |
| Result may look done while core risk remains unproven | Strong fit for Loopora |
| You need to retain, review, reuse, or manage this judgment via Web | Strong fit for Loopora |

Typical examples: React to Vue equivalent ports, billing permission refactors, cross-service payment callback issues, complex data migrations, and production infrastructure changes. High-risk business tasks such as self-service refunds also fit, but they are not required background for understanding Loopora.

A simple test: if you expect to return in round 2, 3, or N asking "is evidence sufficient, is risk acceptable, where should next round focus, can this close now"—don't just run a bare goal; compile that judgment into a Loop.

If you are still deciding whether this task needs Loopora, run the fit guide before installing same-Agent project entries:

```bash
# Installed Loopora command:
loopora fit

# Source checkout before `uv tool install`:
uv run loopora fit

# Or seed the guide with the actual task without asking Loopora to classify it.
loopora fit --task "Migrate billing callbacks without losing idempotency or rollback evidence"
# Fill the completed fit review when you already know the judgment boundary.
loopora fit \
  --task "Migrate billing callbacks without losing idempotency or rollback evidence" \
  --fit-reason "Billing callbacks need multi-round idempotency, replay, and rollback evidence before closure" \
  --why-not-direct "Direct Agent work or unit tests alone would miss replay ordering and closure judgment" \
  --fake-done "Happy-path callback works but retry and duplicate delivery are unproven" \
  --evidence "Idempotency tests, replay proof, rollback dry-run, and reviewer-readable summary" \
  --tradeoffs "Keep scope narrow and fail closed on unproven rollback behavior"

# If direct work is enough, record that decision and stop before setup.
loopora fit \
  --task "Rename one CSS class after a focused visual check" \
  --prefer-direct \
  --direct-path "One focused check and human review fully judge this task"
```

From a source checkout, run fit/help commands from the Loopora checkout with `uv run`, for example `uv run loopora fit`; plain `uv run loopora ...` still only works while the shell is still in the checkout. Bare fit plain output hides Web/init/doctor route details until you run the printed `loopora fit --workdir "$PWD"` rerun from the target project; JSON still keeps blocked `<project-dir>` route actions for tools. After install, run `loopora fit --workdir "$PWD"` from the target project, or run the target-project `uv --directory <Loopora checkout> run loopora start --workdir "$PWD"` route before copying Web/init/doctor commands.

It is a static decision guide, not a classifier: it shows strong-fit signals, cases where direct Agent use or hard checks are better, and the route family to use when the fit is strong. Targetless plain output hides Web/init/doctor command details until you rerun with `--workdir` from the target project, while JSON keeps `<project-dir>` placeholder route actions for automation; `loopora fit --workdir <project>` validates that target, makes setup commands concrete only when the target is usable, and preflights the default local Web port before marking the Web route command ready.

With `--task`, `--fit-reason`, `--fake-done`, `--evidence`, and `--tradeoffs`, it produces a human review draft and a first `/loopora-plan` message shape; optional `--why-not-direct` adds why direct Agent work, `/goal`, hard checks, or project process are not enough for this task. When review inputs are missing and the target is usable, it leads with a review-only Web Fit Guide command, then keeps the terminal completion command as an alternative. The local Fit Guide URL carries supplied fields in a fragment and removes that fragment after filling empty form fields. It still does not declare the task fit automatically or unlock setup before review.

If that review shows no strong-fit signal, stop before installing same-Agent project entries and use the direct Agent, `/goal`, hard checks, or existing project process that can fully judge the task. Use `--prefer-direct` with a direct-path reason (`--direct-path ...`; add `--task ...` only as context) to record that decision: setup routes stay blocked, no copyable `/loopora-plan` message is generated, and the next action remains the direct path. Empty or task-only `--prefer-direct` stays blocked until the direct-path reason is supplied.
When the review is strong but you are not already inside an Agent session, the fit guide also surfaces the Fit Guide/Web choices route so the reviewed task brief can continue through Web conversation, Plan File import, or manual creation instead of forcing an Agent-only start; same-Agent setup remains the path for a current Codex, Claude Code, or OpenCode session.

Use `--language zh` when you want the terminal guide, completion command placeholders, and first-task draft in Chinese. Common locale aliases such as `zh-CN` are accepted and normalized back to `zh` in generated commands.
Semantic aliases `--strong-fit-signal`, `--fake-done-risks`, `--required-evidence`, `--judgment-tradeoffs`, `--direct-path`, and `--why-not-direct` are accepted for review context; generated completion commands still use the canonical shorter `--fit-reason`, `--fake-done`, `--evidence`, and `--tradeoffs` flags for required fields.

## Quick Start

Loopora currently installs from a local source checkout rather than a published package index. You need:

- Python 3.11+
- `uv`
- For real tasks after the isolated demo, at least one Coding Agent: Codex, Claude Code, or OpenCode

Before install, use the source checkout as a decision and identity check. If the fit guide points you to direct Agent use, `/goal`, hard checks, or an existing project process, stop here; no same-Agent project entry needs to be installed. Record that explicit stop from this checkout with `uv run loopora fit --prefer-direct --direct-path ...`; after install, the same decision can use `loopora fit --prefer-direct --direct-path ...`. Add `--task ...` when the task goal is useful context. Empty or task-only `--prefer-direct` stays blocked until the direct-path reason is supplied.

```bash
# 0. Inspect a completed evidence Run or try creation in an isolated playground, without an Agent or provider.
uv run loopora demo --open

# 1. From this Loopora checkout, confirm what code will run and review task fit.
uv run loopora --version
uv run loopora start
uv run loopora fit

# 2. Install a wheel-backed copy only after Loopora is the right route for this project.
uv tool install .
```

Bare `uv run loopora start` and `uv run loopora fit` print a target-project rerun command that preserves the source checkout entry. Use that `--workdir "$PWD"` command from the target project before copying Web/init/doctor route commands; targetless fit hides those route details in plain output while JSON keeps blocked `<project-dir>` route actions for tools. Start/Fit commands generated in compact, detailed, JSON, and Web Fit Guide views also preserve an explicitly configured `LOOPORA_HOME` and the selected terminal language, including shell-safe App-home paths with spaces.

If uv says the tool directory is not on `PATH`, run this before the first installed `loopora` command:

```bash
uv tool update-shell
```

Then restart the shell. From a source checkout, `uv run loopora --version` confirms the package/source identity, and `uv run python -m loopora --help` is a fallback way to confirm the module entry while fixing shell `PATH`.

The default install copies the current checkout into uv's managed tool environment, so later source edits or pulls do not silently change the installed command. Its version output keeps the build-time revision and tree state even after the copy leaves the Git checkout; source-checkout and editable runs prefer the current checkout identity. After reviewing an update from the checkout, refresh it with `uv tool install --force .`. Contributors who intentionally need live source edits can instead use `uv tool install --editable .`; refresh that environment with `uv tool install --force --editable .`. Remove either CLI installation with `uv tool uninstall loopora`. This is separate from `loopora uninstall <agent> --workdir "$PWD"` below, which only removes a same-Agent project entry from one target project.

```bash
# 3. Move to the project you want Loopora to govern.
cd /path/to/your/project
loopora start --workdir "$PWD"
```

Use the route chooser output as the next-step authority. If you are not already inside an Agent session and the review still shows a strong fit, open the Fit Guide/Web choices route:

```bash
loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742
```

Use Fit Guide/Web choices for Web conversation, Plan File import, or manual expert mode when those fit better. Same-Agent setup is for a current Codex, Claude Code, or OpenCode session: `init current` detects a unique host from session presence without printing session identifiers, while Web preselects the same detected host. Missing or conflicting host signals keep setup blocked until you choose an explicit adapter. `--workdir` preselects the target project in Web; bare `loopora serve` still works when you want to choose the project from the Web UI.

If you are already working inside Codex, Claude Code, or OpenCode, install the uniquely detected current-host entry and verify plan handoff in one command:

```bash
loopora init current --workdir "$PWD"
```

The command reports `ready` only after the managed entry is current and the same read-only readiness boundary as doctor allows `/loopora-plan`. `--json` keeps the install result fields and adds `setup_status`, `setup_ready`, and the complete `readiness` report. An installed entry with a blocked handoff is reported as `needs_attention` and exits non-zero.
Add `--language zh` (locale aliases such as `zh-CN` also work) to keep same-Agent setup, explicit adapter fallback, entry checks, and their Doctor/Support follow-up commands in Chinese. The flag changes plain terminal rendering only; `--json` keeps language-neutral status ids, action kinds, and command fields.

If host detection is unavailable or reports multiple hosts, choose the explicit adapter that will continue the task, then run doctor:

| Current Agent | Install command |
| --- | --- |
| Codex | `loopora init codex --workdir "$PWD"` |
| Claude Code | `loopora init claude --workdir "$PWD"` |
| OpenCode | `loopora init opencode --workdir "$PWD"` |

```bash
loopora doctor --workdir "$PWD"
```

Then return to that same Agent session and create the reviewable plan first. Without a completed fit review, send the plain command:

```text
/loopora-plan
```

If you completed `loopora fit --task ... --fit-reason ... --fake-done ... --evidence ... --tradeoffs ...`, keep its complete copyable `/loopora-plan` handoff, then paste it once as a single Agent message only after `init current` or doctor reports the same-Agent handoff ready. It already includes the command and reviewed task judgment. Add optional `--why-not-direct ...` when you want that handoff to explain why direct Agent work, `/goal`, hard checks, or project process are insufficient. This keeps the initial plan anchored in the fit reason, goal, fake-done risk, required evidence, tradeoffs, and any direct-path context without a second turn that can lose context.

Do not paste a `--prefer-direct` decision into `/loopora-plan`; that decision intentionally blocks Loopora setup and keeps the work on the direct path.

Review the READY preview in the Agent. After the preview looks right, run `/loopora-run` in the same Agent session:

```text
/loopora-run
```

Not sure which same-Agent project entry to install? Run `loopora init` without an adapter to list the supported project entries.
In the maintenance commands below, keep using the adapter you chose above: replace `<agent>` with `codex`, `claude`, or `opencode` to match your current Agent host.

To only check whether the same-Agent project entry is complete, still Loopora-managed, and not missing managed protocol files:

```bash
loopora init <agent> --workdir "$PWD" --check
```

You can also check the same entries from the Agent namespace:

```bash
loopora agent <agent> check --workdir "$PWD"
```

`--check` only diagnoses: it does not install, repair, or overwrite. Before install, a failing check means "not installed yet" and prints the install command plus readiness check; after readiness passes, Web links are actionable for creation choices, run status, and details. After install, failed checks mean the managed entry needs attention.

To remove Loopora from one project entry, preview the adapter cleanup scope, uninstall the entry, and confirm readiness again:

```bash
loopora uninstall <agent> --workdir "$PWD" --dry-run
loopora uninstall <agent> --workdir "$PWD"
loopora doctor --workdir "$PWD"
```

The dry run shows removed and kept cleanup counts before anything is deleted. Uninstall removes only files proven Loopora-managed for that project entry; it does not delete Loop records, run artifacts, target project files, global Agent configuration, credentials, or external service history. If `/loopora-plan` or `/loopora-run` still appears in the Agent after uninstall, refresh or restart that Agent host. Reinstall later with the matching `loopora init <agent> --workdir "$PWD"` command.

For a first-use readiness summary across the local package, local App/Web state, default Web entry, and all supported same-Agent project entries:

```bash
loopora doctor --workdir "$PWD"
```

`doctor` is read-only. It exits non-zero when no same-Agent project entry is ready, reports incompatible local App state before Web would fail,
prints the same package/source identity exposed by `loopora --version` and `loopora version --json`, and prints the next install/check or private-archive-then-reset-preview commands instead of changing files.
Its primary action is risk-ordered: incompatible App state leads with the private recovery archive before reset, Web recovery, fit, or setup. With healthy App state and no ready entry, fit remains first; return/refresh guidance appears only after Doctor can name a concrete ready Agent entry. Private and public JSON expose the same `primary_next_action_kind` without making the public report carry local commands.
Use `--language zh` for the Chinese terminal report; aliases such as `zh-CN` normalize to `zh`, and generated Doctor/Fit/Support/same-Agent setup follow-up commands retain that canonical language. `--json` and `--public-json` keep the same language-neutral schema, status values, and action kinds.
From a source checkout, bare `uv run loopora doctor` asks for an explicit target project instead of treating the Loopora checkout as the project; run the printed `doctor --workdir "$PWD"` command from the target project before installing same-Agent entries.
If you plan to start Web on a non-default host or port, pass the same Web target to readiness too,
for example `loopora doctor --workdir "$PWD" --web-host 0.0.0.0 --web-port 9000`;
network binds report token-required guidance or the explicit unsafe opt-in instead of a bare start command.
Add `--strict` when automation should also fail on App/Web warnings.
`loopora dev reset` is a preview by default; deletion still requires reviewing the planned state
and then using the exact `apply_command` / `--yes` command printed by the CLI.
Before deleting useful App or project history, create and verify a private recovery archive:

```bash
loopora recovery create --workdir "$PWD" --output ./loopora-recovery.zip
loopora recovery inspect ./loopora-recovery.zip
```

The archive combines a consistent SQLite App-catalog snapshot with that project's managed `loops`, `runs`, and
`alignment_sessions` directories. It excludes project source, diagnostic logs, Agent entries/inbox files, credentials,
and unknown `.loopora` directories, but it still contains private plans, prompts, transcripts, raw model output,
evidence, settings, and absolute paths. Stop active Runs and planning sessions first, keep the ZIP private, and do not
attach it to public issues. Restore is exact-path recovery rather than migration:

```bash
loopora recovery restore ./loopora-recovery.zip --workdir "$PWD"
```

Restore previews without writing, refuses a different App home/project path or any changed target file, and requires
`--yes` before restoring missing files. Run `loopora doctor --workdir "$PWD"` after restore.
Recovery inspection keeps the purpose explicit: continue a planned App-state recovery with a no-write `dev reset --scope app` preview, use restore preview only when recovering missing files, or rerun Doctor when no recovery write is intended. Add `--language zh` to create, inspect, restore, and dev reset to keep that complete safety path in Chinese; aliases normalize to `zh`, while `--json` status ids and commands remain language-neutral. Ordinary files use byte hashes for conflict protection; the App database uses a read-only consistent SQLite snapshot so WAL or page-layout differences do not look like user changes, while real logical changes still block restore.
Structured create, inspect, and restore output begins with a versioned `recovery_*_summary` and mirrors the same purpose choices, ordered `next_actions`, and readiness dependencies as plain output. When every archived file is already present and identical, restore reports `no_restore_needed`, offers only an optional Doctor check, and never proposes `--yes`.
When App state is incompatible, doctor, start/fit, serve, Web Tools, and reset-preview output put the exact private
archive command before reset; structured actions make reset depend on that archive succeeding. Archive creation reads
the SQLite catalog directly, so an older incompatible schema can still be preserved without opening it as current App state.
If archive creation reports active records after a local crash, first run `loopora status --workdir "$PWD"`. It remains
no-write while distinguishing live work from orphaned local workers; use its scoped `--reconcile` command only after
review, then retry archive creation.
When only Web/App state is blocked, use `loopora dev reset --scope app --workdir "$PWD"`
to preview just the local App database reset instead of clearing project `.loopora` state;
for temporary Web preview or troubleshooting, start, fit, doctor, and serve recovery can also show a disposable
`LOOPORA_HOME="$(mktemp -d)" <current Loopora CLI entry> serve ...` command when the Web target is not already blocked by port/bind preflight; that command does not delete or migrate the blocked App database.
Source-checkout users should keep the generated `uv --directory <Loopora checkout> run loopora` entry rather than shortening it back to bare `loopora`.
When that command comes from `doctor --workdir`, it keeps `--workdir` so the temporary Web preview still opens against the target project.
Add `--json` for automation, or `--public-json` for the redacted doctor report inside public issue support bundles;
the public doctor report keeps package version, source revision when available, coarse project-directory status,
redacted Web readiness blockers and recovery actions, and action summaries
without printing local paths, ports, or commands.
The same check is also available as `loopora diagnose doctor`.

The Agent Native capability contract is intentionally small:

- Execution stays with the current host Agent in its current workdir. Loopora owns managed project entries plus `.loopora/` state, and it does not change model selection, backend routing, permissions, approval mode, global config, skills/plugins, MCP setup, credentials, or environment secrets.
- Activation stays explicit through `/loopora-plan`, `/loopora-run`, or Loopora CLI commands. Host hooks, session-start events, status lines, remote controls, and task trackers are observation or control surfaces, not Loopora phase entries.
- Role handoff uses the host-native mechanism and never starts a nested Codex, Claude Code, or OpenCode CLI. Handoff stays path-based, and multi-role fan-out happens only when the reviewed Loop declares a parallel group.
- Task proof comes from submitted Loopora evidence refs and the task verdict. Approval, host memory, compact summaries, injected editor context, external tool output, hook logs, marketplace/registry state, symlinks, and session archives are hints until submitted as Loopora evidence.
- Packaging stays project-local and thin. Behavior comes from Loopora Core plus managed references; manifests and check commands detect drift; check/init are the explicit update paths; entry visibility is checked through adapter-specific project files and metadata, and some hosts may need a restart or new session to refresh discovery.
- Recovery trusts exact context binding first. When more than one context is possible, Loopora lists recoverable choices instead of guessing the newest host session or taking over historical sessions.

That is the Agent-session happy path: install a same-Agent project entry, confirm readiness, create the reviewed plan in the Agent, then run it from that same Agent session. If you are not already inside an Agent session, open the Fit Guide/Web choices route; Web conversation, Plan File import, and manual expert paths enter the same local records. Same-Agent setup stays separate for users already in Codex, Claude Code, or OpenCode. The next sections explain what the two Agent stages do, how they recover context, and where Web fits as a creation, review, and management surface.

<p align="center">
  <img src="./assets/diagrams/first-run-path.en.svg" alt="Loopora first-use routes: Fit Guide/Web choices when outside an Agent session, same-Agent setup when already inside Codex, Claude Code, or OpenCode, and import/manual expert paths for reviewed plans; all write into the same local Loop record" width="1000" />
</p>

## How `/loopora-plan` Plans

`/loopora-plan` does not start execution immediately. It enters the Loop planning stage: generate, revise, repair, or tighten a reviewable task plan. For first-use readers, think of it as the reusable Loop shape: it turns a long objective into judgment structure that every later run must carry. If run evidence shows evidence rules, verdict conditions, or role responsibilities are wrong, return to `/loopora-plan` or Web review instead of letting the run stage silently change the plan.

Inside Codex, Claude Code, or OpenCode, this alignment stays in the current Agent session. The host asks one focused question when judgment is missing, otherwise presents a draft working agreement and waits for explicit confirmation. Only then does it author a candidate and ask Loopora Core to validate it; it does not start a nested provider CLI. The message-only CLI path is reserved for hosts that cannot continue the dialogue or when you explicitly choose Web review.

Core `READY` means the candidate contract passed structural and semantic validation; it does not automatically prove that the candidate scope matches the confirmed task. Before `/loopora-run`, the Agent shows the preserved task anchor beside the candidate task scope and judgments, and repairs the candidate when they differ.

The plan must carry this task's judgment, not just a task summary. Important task objects, risks, and evidence expectations should enter the task contract, Agent responsibilities, and run flow.

This plan typically contains:

| Artifact | Purpose |
| --- | --- |
| Task contract | Clarifies goal, completion criteria, fake-done patterns, tradeoffs, blocking risks |
| Agent responsibilities | Clarifies what each round should focus on, avoid, deliver, verify |
| Execution strategy | Clarifies what next round should build, prove, repair, narrow, expand, defer |
| Run flow | Clarifies role order, when to inspect, where to return when evidence weak |
| Evidence rules | Clarifies which materials count as strong evidence, which are just self-report or weak |
| Verdict rules | Clarifies when to pass, block, continue, carry explicit residual risk |
| Web preview | Lets you review fit, risks, evidence expectations, responsibilities, closure conditions before run |

<p align="center">
  <img src="./assets/diagrams/plan-judgment-structure.en.svg" alt="A Loopora plan file carries task-local judgment through task contract, Agent responsibilities, execution strategy, run flow, evidence rules, and verdict rules" width="1000" />
</p>

The plan doesn't try to encode all human judgment. It only encodes the part that repeatedly affects this long task: what counts as done, what must be rejected, what evidence is sufficient, which gap comes next, when can task close.

At runtime, Loopora turns these reader-facing pieces into runnable plan: task contract, Agent responsibilities, step order, handoffs, evidence rules stay linked—so Loop can be reviewed before execution and audited after.

## How `/loopora-run` Advances

`/loopora-run` enters the Loop run stage: start, continue, resume, or patch evidence gaps. Agent remains the main executor: it reads code, edits files, runs checks, and explains results. When work needs role handoff, Loopora uses the current host Agent's native role entries instead of starting another nested Codex, Claude Code, or OpenCode CLI process. Loopora's capability contract keeps that boundary explicit: the current host Agent executes in its current workspace, while Loopora manages entries, context binding, role boundaries, evidence, and task verdicts. Loopora keeps each round tied back to the reviewed plan, required evidence, and verdict rules instead of letting the task continue only from chat memory or a bare goal. If you ask to change the judgment standard during this stage, Agent should stop and route you back to `/loopora-plan` or Web review.

Run handoff is progressively disclosed. The managed Agent receives a compact first-step envelope with the work panel, exact host-native role message, coverage IDs, result-file path, and submit command. The work panel distinguishes a step prepared by Loopora Core from role work actually dispatched by the current host, and names the target role plus the evidence gap driving that handoff. Full frozen judgment, capability diagnostics, schemas, and static todo guidance remain available through `--json` and the referenced local contract/template files instead of being repeated on every step.

Newly generated submit commands carry `--attest-role-dispatch` so the host explicitly states that the active target role returned the submitted structured output. Loopora records whether template-assisted wrapping came from that explicit claim or the legacy implicit repair path; neither source label replaces native trace or task evidence.

If current Agent session has exact Loopora binding, `/loopora-run` can resume directly. If workdir has recoverable Loopora runs but current Agent session differs or multiple candidates exist, Loopora should surface choices—not guess which to continue. To create fresh Loop rather than reuse old judgment, return to `/loopora-plan` or Web and explicitly choose fresh start.

Saved Loop reruns follow the same evidence boundary outside the Agent entry. `loopora loops rerun <loop-id>`, the Loop-detail next-run action, and `POST /api/loops/<loop-id>/runs` use the latest terminal Run: an unresolved verdict carries its evidence gaps into the next Run, and a lifecycle failure carries retry context. A result that a user already recorded stays closed and starts clean unless the user explicitly chooses its bounded advisory follow-up. The first Run has no inherited context, and a passing unrecorded Run is not treated as an evidence gap.

Once two terminal Runs provide a comparable target-level trajectory, continuation also changes the next Run's action mode. Progress preserves proven gains and narrows to remaining gaps; no progress requires `change_approach`; regression requires `repair_regression`; mixed movement protects gains while repairing regressions; a changed target contract requires review before any progress claim. Evidence count alone cannot select these modes. The frozen mode and bounded trajectory are included in every role prompt, Agent compact handoff, `loopora loops status <run-id>`, and `GET /api/runs/<run-id>`.

Common recovery paths follow user intent:

| Situation | What Loopora should do |
| --- | --- |
| `/loopora-plan` has no task context yet | It asks for Loopora fit reason, task goal, fake-done risks, required evidence, and judgment tradeoffs before creating a preview; direct-path context is optional |
| Current directory has no Loopora context yet | `/loopora-plan` creates a new candidate Loop by default |
| Current directory already has a spec, candidate Loop, run, or evidence | `/loopora-plan` surfaces available sources first; you can continue, improve, or explicitly start fresh |
| Work stopped halfway and you return to the same Agent session | `/loopora-run` resumes the same run through the exact binding and does not replan |
| You return from a different Agent session or several contexts are recoverable | `/loopora-run` surfaces choices with status and freshness hints; runnable choices show `next_loop_command` and `next_cli_command`, while non-runnable choices send you back to `/loopora-plan` or Web review |
| Previous run ended but evidence is still insufficient | `/loopora-run` starts the next round from the same Loop and focuses on unproven gaps |
| Previous task verdict already passed | `/loopora-run` replays the completed state and does not create an extra run |
| You explicitly want to recreate the plan | Use the fresh path in `/loopora-plan`; old runs and evidence stay history, not current judgment |
| Local Agent binding or context card is damaged | `/loopora-run` returns repair hints; run `loopora init <adapter> --check` first, then repair binding or use `/loopora-plan fresh` |
| Local file cleanup fails while deleting or replacing a plan file | Record deletion can still complete, but Loopora returns `cleanup_warnings` with path and error to clean manually |

A single run roughly follows:

1. Loopora finds reviewed candidate Loop.
2. Agent executes per current round's goal and boundaries.
3. Agent submits work output, checks, explanations, evidence references.
4. Loopora reconciles: what proven, what weak evidence, what remains unproven.
5. Blocking risk can't be packaged as completion.
6. Insufficient evidence pulls next round back to concrete gap.
7. When task can close, Loopora produces reviewable task verdict and residual-risk summary.

That's the difference between Loopora and ordinary prompt or bare `/goal`: prompt mainly shapes next answer; bare goal mainly keeps Agent moving; Loopora keeps same judgment active across multiple rounds.

## Evidence, Tests, and CI

Loopora does not replace tests, CI, or automated proof. Instead, judgments that can be written as tests should first become tests; boundaries that can be proven via proof scripts, schemas, lint, type checks, or real external probes should become strong evidence first.

Loopora handles the layer around that evidence: when evidence is missing, failing, incomplete, or only proves part of the task, the Agent can't package run completion as task completion.

| Evidence Shape | What it means in Loopora |
| --- | --- |
| Tests, CI, evaluation suites, proof scripts | Strongest machine evidence for stable contracts |
| Traceable artifacts, logs, screenshots, structured check results | Useful evidence, but must state what it proves |
| Independent checks or human review conclusions | Can help judgment, but not automatically hard proof |
| Agent's own summary | Readable explanation only; cannot support pass by itself |

If stable tests can fully judge the task, Loopora shouldn't make things heavier. Loopora fits long tasks that need tests and also need continuous judgment about evidence gaps, risk priority, and residual risk.

## Autonomy Boundary

Loopora aims to increase trusted autonomy, not unlimited authorization.

- It doesn't acquire new system permissions for Agent; what Agent can do still depends on host tool, workdir, local permissions.
- Loop's action strategy expresses whether current step is read-only, can write, or can issue final ruling.
- Within the same run, worktree writes should have clear boundaries; parallel review should not become several agents editing the same workspace area at once.
- Task verdict does not replace final human approval; it gives the human a reviewable evidence summary, blockers, and residual-risk notes.
- Local runs create evidence and artifacts; if task touches sensitive code, logs, or business data, handle per local project's security rules.

This boundary matters: Loopora's goal is not to make the Agent more eager to claim completion; it is to make completion harder to claim when proof is missing.

## What Web Can Do

Web is the fuller creation, review, and management surface. You can start a Loop from Agent, or open Web anytime to review evidence, inspect runs, and manage local records. `/loopora-plan` and `/loopora-run` reuse an already-running Web instance only when it belongs to the same Loopora App home. Otherwise they return a relative path and an explicit foreground `serve --open` command; Agent commands never leave a detached Web process behind.

Start local Web and open it in the default browser:

```bash
loopora serve --open --workdir "$PWD" --host 127.0.0.1 --port 8742
```

Before using a custom host or port, run `loopora doctor --workdir "$PWD" --web-host <host> --web-port <port>` with the same target. Doctor checks that port before Web initialization; Doctor, Start, and Fit recognize a responding same-App-home service as ready and keep its requested origin, while configured auth must also match. Doctor and Web Tools then describe the service as running and offer one authoritative open command instead of a second start action in adapter diagnostics. Foreign App homes, non-Loopora occupants, and auth mismatches remain port conflicts that suggest an alternate free port when available. Recovery commands stay aligned with the target project and Web protection mode.

`serve --open` opens the selected page without creating duplicate Web services. If no matching service exists, it starts Web in the foreground: leave the command running and press Ctrl-C to stop it. If a responding service at that origin belongs to the same Loopora App home (and accepts the configured token when auth is enabled), it is reused; the opener exits and the original terminal remains the lifecycle owner. Plain `serve`, another App home, a non-Loopora occupant, or an auth mismatch still reports a port conflict. Generated Start/Fit commands preserve the target project and any task draft in either path. A new `serve` process prints the home, Fit Guide, creation, and support URLs, plus the bind address when it differs. Start from Fit Guide when fit is still uncertain; Web conversation can begin from one task goal and clarify missing judgment before a candidate becomes READY.
Add `--language zh` when the Web-start terminal lifecycle should stay in Chinese. Locale aliases normalize to `zh`, and generated Doctor/Fit/Start/same-Agent retry commands retain it across directory, port/bind, authentication, and App-state recovery. This does not add a language query parameter or change `--json`: browser pages continue to negotiate locale from `Accept-Language`, while structured startup state and commands remain language-neutral.

The default loopback binding needs no token. Binding a non-loopback host fails closed unless you pass a non-blank `--auth-token '<token>'` or explicitly choose `--allow-unsafe-open`; blank or whitespace-only tokens are treated as no protection. Wildcard binds such as `0.0.0.0` are shown as concrete local Fit Guide/create/support URLs plus `<server-host>` network placeholders, not as the primary browser URL. Network mode opens with a token form that stores an httpOnly cookie, still accepts `Authorization: Bearer` for automation, uses server-side absolute paths, and disables native file dialogs.

If an old local App database blocks `serve`, the recovery keeps reset as an explicit preview/apply flow and also prints a disposable `LOOPORA_HOME="$(mktemp -d)" <current Loopora CLI entry> serve ...` command for temporary Web preview without deleting or migrating the blocked App database; source-checkout recovery preserves the generated `uv --directory <Loopora checkout> run loopora` entry.

Without `--open`, use the printed local URL, such as [http://127.0.0.1:8742/fit-guide](http://127.0.0.1:8742/fit-guide).

Web fits these scenarios:

| Scenario | What you can see or do |
| --- | --- |
| Review candidate Loop | Inspect task contract, Agent responsibilities, execution strategy, run flow, evidence rules, verdict rules |
| Observe run | See where the Loop is, and what happened in the latest round |
| Inspect evidence | Separate proven, weak evidence, unproven, blockers, residual risk |
| Compare Runs | See whether stable evidence targets improved, regressed, stayed unchanged, or became incomparable because the contract changed |
| Carry a Run review | Export one curated evidence ZIP from Run detail without bundling workspace files, prompts, transcripts, raw model output, events, or logs |
| Manage same-Agent project entries | Pick a recent project, choose a local folder, or paste a server-side target, then install, update, or remove Codex, Claude Code, OpenCode same-Agent project entries |
| Carry task brief | Continue a complete or partial fit draft into Web conversation while preserving any known task goal, fit reason, fake-done risk, required evidence, judgment tradeoffs, and optional direct-path context. Web clarifies missing items; Plan File import, manual expert mode, and same-Agent setup keep stronger readiness requirements. A draft from another target project stays separate instead of becoming stale context |
| Recover failed or interrupted planning | If the Agent fails before producing a Plan File, or the local service restarts mid-planning, keep the original task and working agreement in the same conversation. Interrupted work becomes resumable instead of staying Active forever; Agent settings/retry remain available, while Plan File repair and sync appear only when a candidate file actually exists. Recoverable conversations stay visible on Home |
| Adjust plans | Edit candidate plan when needed, or create Loop directly from Web |

Same-Agent project entry and Web entry are not separate worlds. Even if a Loop starts inside your Agent, it enters the same local records and can be viewed and managed in Web.

## Contributing, Governance, Community, Support, And Security

Use these public collaboration docs as the entry map:

- Read [CONTRIBUTING.md](./CONTRIBUTING.md) for local setup, quality gates, and design/test boundaries before opening a change.
- Use [GOVERNANCE.md](./GOVERNANCE.md) to understand maintainer-owned decisions such as supported release tags, license/distribution posture, security disclosure, and compatibility or migration risk.
- Follow [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) for respectful, safe, evidence-oriented public collaboration.
- Inspect [CHANGELOG.md](./CHANGELOG.md) for public change history, unreleased adoption notes, and release-note requirements before relying on source-checkout behavior.
- For best-effort usage or setup support, start with `loopora support`, Web Support at `/support`, [SUPPORT.md](./SUPPORT.md), and `loopora support --workdir "$PWD" --public-issue-bundle` when readiness evidence matters. If support output is preview-only, rerun the printed `support --workdir` command before the public issue bundle or public doctor command becomes ready; when the target is missing or not a directory, setup target remains not ready.
- In public issues, paste the public issue support bundle first when readiness or environment evidence matters. Paste public doctor/version output only when the template or a maintainer asks for the underlying report or identity, including `loopora version --json` only when structured identity is requested. Keep support JSON, command lines, JSON command fields, and local Web Support URLs local-only.
- Report vulnerabilities through [SECURITY.md](./SECURITY.md); do not publish exploit details, secrets, tokens, private logs, or sensitive workspace paths in public issues.

## License

This repository currently does not declare a license. Treat redistribution, reuse, third-party code intake, and distribution-term changes as maintainer-approved decisions only; do not infer open-source license rights from public repository access.
