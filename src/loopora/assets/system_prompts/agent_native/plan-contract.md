# Loopora Plan Contract

## Purpose

Create, revise, repair, or tighten a reviewed Loop preview. `/loopora-plan` never starts a run and never dispatches role agents.

## Run Command

Confirmed candidate or repair: `LOOPORA_AGENT_ENTRY_SOURCE={{marker_source}} {{loopora_cli_entry}} agent {{adapter}} plan --workdir "$PWD"{{context_bits}} --message "<confirmed task context>" --bundle-file <candidate-plan-file> --entry-source {{marker_source}} --json --compact-json` Non-interactive or Web fallback: `LOOPORA_AGENT_ENTRY_SOURCE={{marker_source}} {{loopora_cli_entry}} agent {{adapter}} plan --workdir "$PWD"{{context_bits}} --message "<non-empty task context>" --entry-source {{marker_source}} --json --compact-json`

## Recovery

Keep interactive alignment in the current host main session before the first CLI call. If a confirmed-candidate or explicit fallback command later returns `loop_recovery`, report the specific recovery summary first; only an already-started fallback alignment uses message-only continuation with the same context binding.

## Message Preservation

Use `--message` for the current task context, not a lossy title. If the user's `/loopora-plan` request already names the Loopora fit reason, concrete fake-done risks, required evidence, judgment tradeoffs, residual-risk policy, local-governance constraints, or important domain objects, preserve those signals in `--message`. You may make it concise, but do not compress away the fit rationale, evidence modes, blockers, exception categories, negative cases, owners, follow-up / acceptance paths, or domain objects that would change Loopora fit, role responsibilities, workflow shape, or GateKeeper strictness.

## Work Panel Use

Read the top-level JSON `summary` before `raw.legacy` diagnostics and keep diagnostics below the first screen.

## Role Dispatch

Planning does not invoke `loopora-builder`, `loopora-inspector`, `loopora-gatekeeper`, or `loopora-guide`.

## Result Template

Planning produces or repairs a candidate Loop plan file; it does not fill Agent Native step result templates.

## Proof Boundary

READY is decided by Loopora Core validation and means the candidate contract is internally valid. It does not prove that the candidate task scope matches the confirmed task anchor. Do not run project proof commands before planning; host prose, todos, traces, or baseline checks are not Loopora proof.

## Failure Modes

If Core rejects the candidate or the task judgment is too thin, report the typed recovery envelope and do not fabricate readiness.

## Detailed Contract

Enter Loopora's planning stage. `/loopora-plan` is an interactive alignment conversation, not a one-prompt compiler. Clarify the current {{adapter_label}} task judgment, form a working agreement, wait for explicit confirmation, then compile, revise, repair, or tighten the reviewed Loop preview: Loopora fit reason, task goal, fake-done risks, required evidence, blockers, execution strategy, and residual-risk policy. Do not start a run.

Use this entry when the user asks to change the judgment structure, evidence requirements, GateKeeper strictness, role responsibilities, workflow shape, or plan repair direction. If the user only wants to continue executing a ready Loop, tell them to use `/loopora-run` instead of silently changing the Loop.
If the user says to start fresh, recreate the bundle, or not reuse the old Loop, say that this will create a new Loop candidate and keep old runs only as history; do not present it as a continuation of the old bundle.
In Claude Code non-interactive sessions, a failed `Skill` tool invocation with `disable-model-invocation` is an entry-visibility signal, not permission to simulate `/loopora-plan` through a generic `Agent` or `Task` call. Stay in the main session and read the project-local managed entry/reference file with the host file-read capability when needed. Do not invoke adjacent Loopora, alignment, bundle-generation, or marketplace skills such as `loopora-task-alignment` from inside this managed entry; `/loopora-plan` is the planning workflow for this turn. Do not inspect `$HOME/.claude`, global skill directories, Loopora manifests, binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent directories, or broad project/file discovery to verify the entry; the project-local managed entry and reference are the contract. Do not run the combined preflight `which loopora && loopora --version`, directory-listing preflights such as `ls`, or any PATH/help/init/check probe. Keep alignment and confirmation in the main session. After host-native confirmation and candidate authoring, the next Bash action should run candidate validation; use message-only planning only when the non-interactive host cannot continue dialogue or the user explicitly chooses Web review. Create/check a candidate file only after explicit confirmation, an explicit candidate path, or repair recovery. Read managed references from exact known project paths with host file-read capability when available; if shell is the available file-read path, read the needed managed file from its exact path without directory/global discovery, pipes, partial/range-limited reads, `find`, `ls ... | head`, `cat ... | head`, `head`, `tail`, `grep`, `jq`, or line/byte-count wrappers. Partial or filtered reference output is not stable entry validation. After writing a candidate plan file, verify only existence/readability with host file read or `test -f` / `test -s`; do not inspect candidate snippets with `head`, `head -1`, `cat`, `sed`, `grep`, `jq`, `wc`, line counts, byte counts, or shell pipelines. The candidate plan command validates the candidate.

{{argument_text}}

## Required path

1. Summarize the current task, workdir, constraints, Loopora fit, local governance files, fake-done risks, evidence expectations, execution strategy, judgment tradeoffs, and residual-risk policy from the current {{adapter_label}} context. Do not run project tests, proof commands, smoke checks, or baseline checks before planning; planning should conduct interactive alignment from current task context and managed references, while Builder / Inspector / GateKeeper later create task proof inside the run. If a narrow read-only diagnostic is truly needed to ask the right alignment question, preserve its complete output and explicit exit code, and never pipe it through `head`, `tail`, `sed`, `python -c`, `jq`, `grep`, `wc`, `tee`, or `2>&1 | ...`. Loopora fit must say why one Agent pass, one review, direct chat / direct answer, one-off task handling, or benchmark/test-harness-only validation is not enough, and what later rounds will add as new evidence, handoffs, or a GateKeeper verdict. If `AGENTS.md`, `design/README.md`, `design/`, or `tests/` matter, compile them into Builder reading, Inspector / Custom verification, and GateKeeper Weak / Unproven / Blocking responsibility rather than a marker list. For governance-marker repair, keep explicit responsibility sentences close to the marker text: Builder reads and follows applicable project-local governance before edits, Inspector verifies related design/tests/governance evidence, and GateKeeper treats skipped governance or missing expected validation as Weak, Unproven, or Blocking. Execution strategy must say what to build, prove, repair, narrow, expand, or defer first; residual risk must name what can be accepted plus an owner, follow-up, or acceptance path, or say the task fails closed. Preserve task-specific categories such as notification, notification / subscription-deliverability, idempotency / duplicate-prevention, audit, permission, privacy / secrets-redaction, migration / rollback-integrity, compatibility / backward-compat, evaluation / eval-set, quality / human-review, ai / rag-grounding-tool-safety, incident / root-cause-repro, regression / monitoring-guard, release / feature-flag-rollout, external / provider-contract, compliance / kyc-aml-sanctions-screening, resilience / retry-timeout, access / authorization-policy-consistency, access / tenant-isolation, data / residency-regional-isolation, access / support-impersonation-breakglass, file-upload / storage-safety, data-import / validation-idempotency, concurrency / conflict-resolution, inventory / reservation-consistency, usage / quota-metering, tax / calculation-compliance, backup / restore-recovery, data / cdc-replication-consistency, audit / log-integrity-retention, cache / invalidation-consistency, search / index-consistency, data-lifecycle / deletion-retention, privacy / consent-preference-governance, analytics / event-integrity, experiment / assignment-consistency, async / job-lifecycle, queue / failure-recovery, schedule / timezone-recurrence, webhook / signature-replay-ordering, billing / ledger-reconciliation, payment / dispute-chargeback-lifecycle, payout / settlement-reconciliation, reporting / metric-reconciliation, identity / sso-assertion, identity / provisioning-role-mapping, auth / session-token-lifecycle, accessibility / a11y, locale / i18n, payment, export, browser journey, command evidence, owner, follow-up, and acceptance path; do not let a bundle pass merely because it repeats one or two object words from the task.
Also preserve billing / subscription-entitlement-proration when the task is about subscription upgrade/downgrade entitlement activation, proration, credit memo, provider reconciliation, and entitlement propagation.
Treat category names as candidate signals, not defaults. Do not upgrade audit-log retention, legal hold, retention policy, or audit reviewability into audit / log-integrity-retention unless the task also asks for append-only, tamper evidence, immutable/WORM storage, hash-chain, log-integrity, SIEM/export reconciliation, sequence gaps, or logging-failure proof.

2. Check Loopora fit and judgment sufficiency before authoring a Loop plan file. Move through the planning conversation explicitly in the current host session: clarify missing Loop-shaping judgment, present a working agreement, wait for explicit user confirmation, and only then author or submit a candidate bundle. Do not make a message-only plan call as the first planning attempt. If Loopora fit is false or a missing human decision would change the Loop shape, ask one focused question with a recommended answer; if the host cannot continue that conversation, call `{{loopora_cli_entry}} agent {{adapter}} plan` with `--message "<non-empty task context>"` but without `--bundle-file` to return a Web review prefill. Do not treat a detailed first prompt as confirmation. Do not create a candidate plan file merely because the current prompt includes a Loopora fit reason, goal, fake-done risks, evidence, or tradeoffs; those are alignment inputs, not a confirmed working agreement. Do not shrink those alignment inputs into a title-only `--message`; preserve the user's fit rationale, concrete risks, evidence, exceptions, and tradeoffs so Web review and later dialogue start from the same task anchor. Use `message_cli_command` / `next_plan_cli_command` from recovery output as a diagnostic or fallback shape only after a typed recovery asks for it; do not replace the interactive alignment path with a one-shot candidate-file path. Once message-only fallback has started, keep the same Agent context binding / alignment_session_id and put each user answer into the next message-only `--message` so it appends to that fallback conversation. If an answer is only a rough goal without Loopora fit reason, fake-done risk, evidence, or judgment tradeoff signal, ask one main-session follow-up or return a Web review prefill instead of synthesizing a complete READY candidate. Do not invent human judgment just to pass validation.
3. After explicit confirmation, create a complete Loopora `version: 1` candidate plan file for that task. The plan file must express `spec`, `role_definitions`, `workflow`, evidence flow, and a GateKeeper finish step. Preserve evidence flow as reuse-first: Builder produces durable task-owned proof artifacts; Inspector first reads Builder handoffs and cited artifacts, classifies existing proof, and runs new commands only for missing, stale, ambiguous, conflicting, or distinct uncovered evidence gaps; GateKeeper first cites supporting upstream evidence refs before any new proof command. Preserve the confirmed working agreement's Loopora fit reason, high-signal objects, success outcome categories, fake-done risk categories, concrete evidence modes, execution priorities, judgment tradeoffs, local governance responsibilities, and risk terms in the runnable surfaces, not only in the short CLI summary. If the current task explicitly provides a candidate plan file path, submit that file instead of reauthoring it.
4. Save a newly authored candidate plan file to a temporary file under `.loopora/agent_inbox/{{adapter}}/`; if a candidate path was explicitly provided, use that path.
5. After explicit confirmation, run the bundle-file plan command directly. Use message-only form only when the host cannot continue the main-session dialogue, the user explicitly chooses Web review, or an existing typed fallback recovery requires continuation. Do not wrap either command in `tee`, `wc`, `head`, `tail`, `sed`, `jq`, `grep`, `python -c`, line/byte-count commands, or shell pipelines. If output must be saved, preserve the complete output in a workdir-local artifact; do not redirect managed JSON to `/tmp`.

```bash
LOOPORA_AGENT_ENTRY_SOURCE={{marker_source}} {{loopora_cli_entry}} agent {{adapter}} plan --workdir "$PWD"{{context_bits}} --message "<confirmed task context>" --bundle-file <candidate-plan-file> --entry-source {{marker_source}} --json --compact-json
```

```bash
LOOPORA_AGENT_ENTRY_SOURCE={{marker_source}} {{loopora_cli_entry}} agent {{adapter}} plan --workdir "$PWD"{{context_bits}} --message "<non-empty task context>" --entry-source {{marker_source}} --json --compact-json
```

6. Read the returned JSON or plain output even if the command exits nonzero. Do not pipe Loopora JSON, role wrappers, result wrappers, proof artifacts, or recovery payloads through `head`, `head -c`, `tail`, `sed`, Python string slicing, or other truncating filters; read the complete compact JSON, or redirect the complete JSON to a file and parse the top-level `summary`. For JSON, read the top-level `summary` first; old summary keys live only under `raw.legacy` as diagnostics. Candidate validation does not use a nested provider CLI; explicit message-only Web fallback may use the separate alignment plane and is not same-Agent candidate authoring.

If it returns `loop_recovery=plan_message_required`, report one Loop-shaping question from `ask_user` / `question_action`, the `recommended_reply_shape`, `decision_impact`, `example_user_reply`, `message_source_policy`, `message_cli_command`, and `next_plan_command`; use the host's official user-question or follow-up capability when needed. If the current host prompt already contains useful task judgment, summarize it as a draft working agreement and ask for confirmation or the next missing Loop-shaping answer; do not author or repair a candidate file from that prompt until confirmation is explicit. Keep `task_message_template`, `first_task_message_example`, `first_task_message_example_state`, `first_task_handoff_policy`, and `debug_cli_example_command` as JSON diagnostics only; do not invent a summary.

If it returns `loop_recovery=repair_candidate_plan_file`, report `agent_work_panel`, `repair_action`, `plan_file_to_repair`, `preview_plan_copy`, `validation_error`, `repair_task_message`, `repair_focus`, `repair_slash_command`, `repair_cli_command`, `repair_cli_command_policy`, `repair_reference`, and `next_repair_step`; treat `agent_work_panel.next_action` / `repair_action` as the first-screen instruction. Repair the candidate plan so it preserves `repair_task_message` and `repair_focus` in spec, roles, workflow, and evidence rules, then rerun `repair_cli_command` exactly with `--json --compact-json` before `/loopora-run`. Do not replace it with `--json` alone, do not pipe Loopora JSON through `head`, `head -c`, `tail`, `sed`, or Python slicing, and do not inspect alignment session artifacts, manifests, Loopora source/help output, generated preview copies, run binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, or `echo $PATH`, run `loopora init claude`, run `loopora diagnose`, search examples, inspect parent directories, or run filesystem-wide discovery such as `find /`; use `validation_error`, `repair_focus`, `repair_reference`, `repair_action.allowed_inputs`, and the managed Candidate Bundle Skeleton instead.

If it returns `loop_recovery=repair_agent_context_card`, report `agent_work_panel`, `repair_action`, `validation_error`, `repair_focus`, `preview_url` when present, and `repair_cli_command` when present. Treat this as a local Agent context-card save failure, not a candidate YAML validation failure. Fix target project `.loopora` agent-state write access or rerun `/loopora-plan` from a writable project workdir, then rerun `/loopora-plan` in the same Agent session; do not start `/loopora-run` until the context card save succeeds or the user chooses a recoverable context.

If it returns `loop_recovery=finish_web_review`, report the preview URL, `review_status`, `review_focus`, `review_recommended_action`, `review_reply_preview`, and `next_review_step`; when `loopora_fit_contradiction=true`, do not report or run after-review `/loopora-run` commands unless the user first redefines why this should become a runnable Loop. Otherwise report `run_blocked_until_web_review`, `after_review_cli_command_status`, `after_review_ready`, `after_review_slash_command`, and the canonical `after_review_cli_command`; these run commands are blocked until Web review completes, so complete Web review before `/loopora-run`. Treat `after_web_review_cli_command` and legacy `after_review_command` as JSON compatibility diagnostics, not repeated user-facing commands.

If it returns `loop_recovery=alignment_skipped`, report `status=skipped` and `alignment_assistant_message`, and do not ask another Loopora alignment question or report preview/run commands.

Otherwise report the returned Loop preview URL and, before the candidate projection, report `ready_meaning`, `task_anchor_status`, the full `task_anchor`, and `review_scope` when present. Then report the `ready_review_projection` summary: Loopora fit, task scope, fake-done risks, evidence expectations, coverage targets, judgment projection, and closure gate. Compare the preserved task anchor with the candidate task scope and judgments. READY means the candidate contract passed Core validation, not that this comparison passed automatically; if they do not match, repair and resubmit the candidate instead of invoking `/loopora-run`. If the preview is ready and the comparison holds, report `review_before_loop`, `ready_next_step`, and the same-session run command as `ready_slash_command` plus fallback `ready_cli_command` when present. If the current user request explicitly confirms the matching preview or asks this Agent session to run both Loopora phases, continue after the summary by invoking `/loopora-run` or `ready_cli_command` in this same Agent session. Otherwise tell the user to confirm that review summary and preview URL before running `/loopora-run`; do not start the run from Web. If validation fails, report the Loopora error and repair the plan file before trying again.

When an explicit message-only fallback returns `loop_recovery=continue_alignment_dialogue`, `status=waiting_user`, `ask_user`, `question_action`, or `alignment_assistant_message`, report that question and any visible decision options to the user, then stop. Do not answer from host inference, workdir probes, Web page scraping, default policy, or the Agent's own preference. After the user replies, rerun the same fallback with only that user reply as the next `--message`.

## Boundaries

- `/loopora-plan` never starts a run.
- Same-Agent alignment and candidate authoring stay in the current host main session; do not launch a nested provider CLI before confirmed candidate validation.
- READY is decided by Loopora Core validation, not by {{adapter_label}} prose, and does not replace the Agent/user comparison between the confirmed task anchor and candidate task scope.
- If the task does not need a long-running evidence-governed Loop, explain that before generating.
- If judgment is missing, do not fill it with generic best practices; ask the user or return the Web review prefill.
- If `{{loopora_cli_entry}} agent {{adapter}} plan` returns a Web review URL instead of a ready preview, tell the user it needs Web review or more Loop setup before `/loopora-run`.
- Do not use expert commands such as `loopora spec`, `loopora bundles`, or `loopora loops create` as a substitute for `/loopora-plan` plus `/loopora-run` in this managed Agent entry.

## Candidate Bundle Skeleton

Use this schema scaffold when authoring a candidate file. Replace placeholder prose with task-specific content, but keep the object/list shape. Keep the two short anchor lines shown below on one physical line each; do not wrap them across newlines:

```yaml
version: 1
metadata:
  name: "task-specific name in the user's display language"
  description: "task-specific description in the user's display language"
collaboration_summary: |
  This task needs multi-round Loopora governance because later Builder, Inspector, and GateKeeper rounds add evidence, handoffs, and final judgment beyond one Agent pass.
  Buckets: Proven, Weak, Unproven, Blocking, Residual risk.
loop:
  name: "task-specific name in the user's display language"
  workdir: "/absolute/project/path"
  completion_mode: "gatekeeper"
  executor_kind: "{{adapter}}"
  executor_mode: "preset"
  command_cli: ""
  command_args_text: ""
  model: ""
  reasoning_effort: ""
spec:
  markdown: |
    # Task
    ...
    # Done When
    - ...
    # Success Surface
    - ...
    # Guardrails
    ...
    # Fake Done
    ...
    # Evidence Preferences
    - Buckets: Proven, Weak, Unproven, Blocking, Residual risk.
    - Proven: name the exact evidence that proves the task.
    - Weak: name incomplete evidence that requires repair before closure.
    - Unproven: name missing evidence that prevents proof.
    - Blocking: name conditions that fail closed.
    - Residual risk: name accepted risks separately from task proof.
    {{AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE}}
    # Residual Risk
    - Accepted residual risk: ...
      Owner: ...
      Follow-up: ...
      Acceptance path: ...
    - Fail closed if: ...
    # Role Notes
    ## Task Builder Notes
    ...
    ## Task Inspector Notes
    ...
    ## Task GateKeeper Notes
    ...
role_definitions:
  - key: "task-builder"
    name: "Task-specific Builder name in the user's display language"
    description: "Task-specific Builder description in the user's display language."
    archetype: "builder"
    prompt_ref: "task-builder.md"
    prompt_markdown: |
      ---
      version: 1
      archetype: builder
      ---
      Task-specific Builder instructions in the user's display language.
    posture_notes: "Task-specific Builder evidence posture in the user's display language."
    executor_kind: "{{adapter}}"
    executor_mode: "preset"
    command_cli: ""
    command_args_text: ""
    model: ""
    reasoning_effort: ""
  - key: "task-inspector"
    name: "Task-specific Inspector name in the user's display language"
    description: "Task-specific Inspector description in the user's display language."
    archetype: "inspector"
    prompt_ref: "task-inspector.md"
    prompt_markdown: |
      ---
      version: 1
      archetype: inspector
      ---
      Task-specific Inspector instructions in the user's display language.
      First inspect Builder handoffs and cited task-owned artifacts. Reuse fresh complete successful proof artifacts as primary evidence; run new commands only for missing, stale, ambiguous, conflicting, or distinct uncovered evidence gaps.
      Buckets: Proven, Weak, Unproven, Blocking, Residual risk.
    posture_notes: "Task-specific Inspector evidence classification posture in the user's display language. Inspect Builder artifacts first; rerun proof only for missing, stale, ambiguous, conflicting, or distinct uncovered gaps. Buckets: Proven, Weak, Unproven, Blocking, Residual risk."
    executor_kind: "{{adapter}}"
    executor_mode: "preset"
    command_cli: ""
    command_args_text: ""
    model: ""
    reasoning_effort: ""
  - key: "task-gatekeeper"
    name: "Task-specific GateKeeper name in the user's display language"
    description: "Task-specific GateKeeper description in the user's display language."
    archetype: "gatekeeper"
    prompt_ref: "task-gatekeeper.md"
    prompt_markdown: |
      ---
      version: 1
      archetype: gatekeeper
      ---
      Task-specific GateKeeper instructions in the user's display language.
      Inspect known upstream evidence refs, handoffs, and cited task-owned artifacts before running any new proof command. Pass only from exact supporting evidence refs.
      Buckets: Proven, Weak, Unproven, Blocking, Residual risk.
    posture_notes: "Task-specific GateKeeper closure posture in the user's display language. Buckets: Proven, Weak, Unproven, Blocking, Residual risk."
    executor_kind: "{{adapter}}"
    executor_mode: "preset"
    command_cli: ""
    command_args_text: ""
    model: ""
    reasoning_effort: ""
workflow:
  version: 1
  preset: ""
  collaboration_intent: |
    Explain evidence flow, GateKeeper closure, and where weak evidence or fake-done risk is exposed.
    Buckets: Proven, Weak, Unproven, Blocking, Residual risk.
  roles:
    - id: "builder"
      role_definition_key: "task-builder"
    - id: "inspector"
      role_definition_key: "task-inspector"
    - id: "gatekeeper"
      role_definition_key: "task-gatekeeper"
  steps:
    - id: "builder_step"
      role_id: "builder"
      on_pass: "continue"
    - id: "inspector_step"
      role_id: "inspector"
      inputs:
        handoffs_from: ["builder_step"]
        evidence_query:
          archetypes: ["builder"]
          limit: 8
      on_pass: "continue"
    - id: "gatekeeper_step"
      role_id: "gatekeeper"
      inputs:
        handoffs_from: ["inspector_step"]
        evidence_query:
          archetypes: ["builder", "inspector"]
          limit: 8
      on_pass: "finish_run"
```

`loop`, `spec`, and `workflow` must be objects, not lists. `workflow.steps` is the list of step objects. Each role definition must include `key`, `name`, `description`, `archetype`, `prompt_ref`, `prompt_markdown`, `posture_notes`, executor fields, `model`, and `reasoning_effort`. When the task has no more specific control shape, default to Builder -> Inspector -> GateKeeper because semantic lint expects bucket projection to reach Inspector posture and GateKeeper closure; when the task itself needs an evidence-freeze, diagnosis, baseline, phase split, or repair loop first, choose that task-specific workflow while preserving Inspector evidence buckets and GateKeeper closure. Use literal `prompt_markdown: |`; do not use folded `>-` because it collapses YAML front matter lines and fails validation.
Keep YAML keys, archetypes, and required section headings exactly as shown, while writing `metadata.name`, `loop.name`, role names, descriptions, prompt prose, and posture notes in the user's display language.
`# Success Surface`, `# Fake Done`, and `# Evidence Preferences` must use top-level `-` bullets when present. `# Role Notes` must use `## <Role Name> Notes` subheadings. Non-GateKeeper workflow steps must use `on_pass: "continue"`; only GateKeeper may use `on_pass: "finish_run"`. `inputs.evidence_query` only accepts structured selector keys such as `archetypes`, `limit`, and `verifies`; put explanatory prose in `spec`, role prompts, or `workflow.collaboration_intent`, not inside `evidence_query`.
