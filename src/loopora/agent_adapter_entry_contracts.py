from __future__ import annotations

from loopora.agent_adapter_entry_sections import AdapterEntrySection, render_adapter_entry_sections
from loopora.residual_risk_prompt_guidance import AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE
from loopora.agent_adapter_run_contract import (
    agent_native_loop_body as agent_native_loop_body,
    agent_native_run_entry_contract as agent_native_run_entry_contract,
    agent_run_section_overview as agent_run_section_overview,
)
from loopora.agent_adapter_role_contracts import agent_native_dispatch_guidance


def _agent_plan_sections(*, adapter: str, marker_source: str, context_bits: str) -> list[AdapterEntrySection]:
    return [
        AdapterEntrySection(
            "Purpose",
            (
                "Create, revise, repair, or tighten a reviewed Loop preview. `/loopora-plan` never starts a run and never "
                "dispatches role agents."
            ),
        ),
        AdapterEntrySection(
            "Run Command",
            (
                f"`LOOPORA_AGENT_ENTRY_SOURCE={marker_source} loopora agent {adapter} plan --workdir \"$PWD\"{context_bits} "
                f"--message \"<non-empty short task summary>\" --bundle-file <candidate-plan-file> "
                f"--entry-source {marker_source} --json --compact-json`"
            ),
        ),
        AdapterEntrySection(
            "Recovery",
            (
                "If planning returns `loop_recovery`, report the specific recovery summary first. For missing judgment, ask one "
                "main-session Loop-shaping question and put the user's answer into `--message`."
            ),
        ),
        AdapterEntrySection(
            "Work Panel Use",
            "Read the top-level JSON `summary` before `raw.legacy` diagnostics and keep diagnostics below the first screen.",
        ),
        AdapterEntrySection(
            "Role Dispatch",
            "Planning does not invoke `loopora-builder`, `loopora-inspector`, `loopora-gatekeeper`, or `loopora-guide`.",
        ),
        AdapterEntrySection(
            "Result Template",
            "Planning produces or repairs a candidate Loop plan file; it does not fill Agent Runner result templates.",
        ),
        AdapterEntrySection(
            "Proof Boundary",
            "READY is decided by Loopora Core validation. Do not run project proof commands before planning; host prose, todos, traces, or baseline checks are not Loopora proof.",
        ),
        AdapterEntrySection(
            "Failure Modes",
            "If Core rejects the candidate or the task judgment is too thin, report the typed recovery envelope and do not fabricate readiness.",
        ),
    ]


def agent_plan_contract(
    adapter: str,
    adapter_label: str,
    marker_source: str,
    *,
    context_arg: str = "",
    supports_arguments: bool = False,
) -> str:
    context_bits = f" {context_arg}" if context_arg else ""
    argument_text = (
        "\nIf `$ARGUMENTS` contains `fresh`, create a new candidate and keep old runs only as history. "
        "If `$ARGUMENTS` contains a candidate plan file path, submit that file instead of authoring a different one.\n"
        if supports_arguments
        else "\nIf the user supplies `fresh`, create a new candidate and keep old runs only as history. "
        "If they supply a candidate plan file path, submit that file instead of authoring a different one.\n"
    )
    section_overview = render_adapter_entry_sections(
        _agent_plan_sections(adapter=adapter, marker_source=marker_source, context_bits=context_bits)
    )
    return f"""# Loopora Plan Contract

{section_overview}

## Detailed Contract

Enter Loopora's planning stage. Compile, revise, repair, or tighten the current {adapter_label} task judgment into a reviewed Loop preview: task goal, fake-done risks, required evidence, blockers, execution strategy, and residual-risk policy. Do not start a run.

Use this entry when the user asks to change the judgment structure, evidence requirements, GateKeeper strictness, role responsibilities, workflow shape, or plan repair direction. If the user only wants to continue executing a ready Loop, tell them to use `/loopora-run` instead of silently changing the Loop.
If the user says to start fresh, recreate the bundle, or not reuse the old Loop, say that this will create a new Loop candidate and keep old runs only as history; do not present it as a continuation of the old bundle.
In Claude Code non-interactive sessions, a failed `Skill` tool invocation with `disable-model-invocation` is an entry-visibility signal, not permission to simulate `/loopora-plan` through a generic `Agent` or `Task` call. Stay in the main session, read the project-local managed entry/reference file if needed with the host file-read capability, and run the explicit `loopora agent {adapter} plan` Bash command with the same entry source. Do not invoke adjacent Loopora, alignment, bundle-generation, or marketplace skills such as `loopora-task-alignment` from inside this managed entry; `/loopora-plan` is the planning workflow for this turn. Do not inspect `$HOME/.claude`, global skill directories, Loopora manifests, binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, `echo $PATH`, `loopora --version`, `loopora --help`, `loopora init claude`, `loopora agent claude check`, parent directories, or broad project/file discovery to verify the entry; the project-local managed entry and reference are the contract, and the explicit plan command is the capability check. Do not run the combined preflight `which loopora && loopora --version`, directory-listing preflights such as `ls`, or any PATH/help/init/check probe before the primary plan command; after reading the managed entry/reference, the next Bash action should create/check the candidate file or run the primary plan command. Do not read managed references through shell directory discovery, `find`, `ls ... | head`, `cat ... | head`, `sed`, `tail`, `grep`, `jq`, or line/byte-count wrappers; those are command-output filters, not stable entry validation. After writing a candidate plan file, verify only existence/readability with host file read or `test -f` / `test -s`; do not inspect candidate snippets with `head`, `head -1`, `cat`, `sed`, `grep`, `jq`, `wc`, line counts, byte counts, or shell pipelines. The primary plan command validates the candidate.
{argument_text}
## Required path

1. Summarize the current task, workdir, constraints, Loopora fit, local governance files, fake-done risks, evidence expectations, execution strategy, judgment tradeoffs, and residual-risk policy from the current {adapter_label} context. Do not run project tests, proof commands, smoke checks, or baseline checks before the primary `loopora agent {adapter} plan` command; planning should author the Loop contract from current task context and managed references, while Builder / Inspector / GateKeeper later create task proof inside the run. If a narrow read-only diagnostic is truly needed to author the plan, preserve its complete output and explicit exit code, and never pipe it through `head`, `tail`, `sed`, `python -c`, `jq`, `grep`, `wc`, `tee`, or `2>&1 | ...`. Loopora fit must say why one Agent pass, one review, direct chat / direct answer, one-off task handling, or benchmark/test-harness-only validation is not enough, and what later rounds will add as new evidence, handoffs, or a GateKeeper verdict. If `AGENTS.md`, `design/README.md`, `design/`, or `tests/` matter, compile them into Builder reading, Inspector / Custom verification, and GateKeeper Weak / Unproven / Blocking responsibility rather than a marker list. For governance-marker repair, keep explicit responsibility sentences close to the marker text: Builder reads and follows applicable project-local governance before edits, Inspector verifies related design/tests/governance evidence, and GateKeeper treats skipped governance or missing expected validation as Weak, Unproven, or Blocking. Execution strategy must say what to build, prove, repair, narrow, expand, or defer first; residual risk must name what can be accepted plus an owner, follow-up, or acceptance path, or say the task fails closed. Preserve task-specific categories such as notification, audit, permission, payment, export, browser journey, command evidence, owner, follow-up, and acceptance path; do not let a bundle pass merely because it repeats one or two object words from the task.
2. Check Loopora fit and judgment sufficiency before authoring a Loop plan file. If Loopora fit is false or a missing human decision would change the Loop shape, ask one focused question; if the host cannot continue that conversation or cannot author a candidate bundle in this environment, call `loopora agent {adapter} plan` with `--message "<non-empty short task summary>"` but without `--bundle-file` to return a Web review prefill. Do not make a message-only plan call as the first planning attempt when the current host prompt already contains a usable goal, fake-done risks, required evidence, and judgment tradeoffs, especially when the user asked this Agent session to use both Loopora phases. In that case, do not call `AskUserQuestion` just to restate it; use the prompt as `--message`, create the candidate plan file in step 3, and run the required command with `--bundle-file`. Use `message_cli_command` / `next_plan_cli_command` from recovery output as a diagnostic or fallback shape only after a typed recovery asks for it; do not replace the primary candidate-file path with a message-only prefill. When retrying from the user's answer, put that answer into `--message`; if the answer is only a rough goal without fake-done risk, evidence, or judgment tradeoff signal, ask one main-session follow-up or return a Web review prefill instead of synthesizing a complete READY candidate. Do not invent human judgment just to pass validation.
3. Create a complete Loopora `version: 1` candidate plan file for that task. The plan file must express `spec`, `role_definitions`, `workflow`, evidence flow, and a GateKeeper finish step. Preserve evidence flow as reuse-first: Builder produces durable task-owned proof artifacts; Inspector first reads Builder handoffs and cited artifacts, classifies existing proof, and runs new commands only for missing, stale, ambiguous, conflicting, or distinct uncovered evidence gaps; GateKeeper first cites supporting upstream evidence refs before any new proof command. Preserve the current task's Loopora fit reason, high-signal objects, success outcome categories, fake-done risk categories, concrete evidence modes, execution priorities, judgment tradeoffs, local governance responsibilities, and risk terms in the runnable surfaces, not only in the short CLI summary. If the current task explicitly provides a candidate plan file path, submit that file instead of reauthoring it.
4. Save a newly authored candidate plan file to a temporary file under `.loopora/agent_inbox/{adapter}/`; if a candidate path was explicitly provided, use that path.
5. Run the plan command directly. Do not wrap it in `tee`, `wc`, `head`, `tail`, `sed`, `jq`, `grep`, `python -c`, line/byte-count commands, or shell pipelines. If you need to save output, redirect the complete output to a workdir-local artifact first and read that preserved file as JSON; do not redirect managed JSON to `/tmp`.

```bash
LOOPORA_AGENT_ENTRY_SOURCE={marker_source} loopora agent {adapter} plan --workdir "$PWD"{context_bits} --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source {marker_source} --json --compact-json
```

6. Read the returned JSON or plain output even if the command exits nonzero. Do not pipe Loopora JSON, role wrappers, result wrappers, proof artifacts, or recovery payloads through `head`, `head -c`, `tail`, `sed`, Python string slicing, or other truncating filters; read the complete compact JSON, or redirect the complete JSON to a file and parse the top-level `summary`. For JSON, read the top-level `summary` first; old summary keys live only under `raw.legacy` as diagnostics. The summary is the compact planning decision before the full session payload, including the agent surface summary so the host can confirm `/loopora-plan` and `/loopora-run` are project-local Agent entries, role dispatch is host-native, and nested provider CLIs are not used. If it returns `loop_recovery=plan_message_required`, report one Loop-shaping question from `ask_user` / `question_action`, the `recommended_reply_shape`, `decision_impact`, `example_user_reply`, `message_source_policy`, `message_cli_command`, and `next_plan_command`; use the host's official user-question or follow-up capability when needed, but if the current host prompt already contains the required task contract, author or repair a candidate file from that prompt and rerun the required `--bundle-file` command instead of rerunning a message-only prefill. Keep `task_message_template`, `first_task_message_example`, and `debug_cli_example_command` as JSON diagnostics only; do not invent a summary. If it returns `loop_recovery=repair_candidate_plan_file`, report `agent_work_panel`, `repair_action`, `plan_file_to_repair`, `preview_plan_copy`, `validation_error`, `repair_task_message`, `repair_focus`, `repair_slash_command`, `repair_cli_command`, `repair_cli_command_policy`, `repair_reference`, and `next_repair_step`; treat `agent_work_panel.next_action` / `repair_action` as the first-screen instruction. Repair the candidate plan so it preserves `repair_task_message` and `repair_focus` in spec, roles, workflow, and evidence rules, then rerun `repair_cli_command` exactly with `--json --compact-json` before `/loopora-run`. Do not replace it with `--json` alone, do not pipe Loopora JSON through `head`, `head -c`, `tail`, `sed`, or Python slicing, and do not inspect alignment session artifacts, manifests, Loopora source/help output, generated preview copies, run binary/PATH probes such as `which loopora`, `command -v loopora`, `type loopora`, or `echo $PATH`, run `loopora init claude`, run `loopora diagnose`, search examples, inspect parent directories, or run filesystem-wide discovery such as `find /`; use `validation_error`, `repair_focus`, `repair_reference`, `repair_action.allowed_inputs`, and the managed Candidate Bundle Skeleton instead. If it returns `loop_recovery=finish_web_review`, report the preview URL, `review_status`, `review_focus`, `run_blocked_until_web_review`, `after_review_cli_command_status`, `after_review_ready`, `after_review_slash_command`, `after_web_review_cli_command`, `after_review_cli_command`, and legacy `after_review_command`; these run commands are blocked until Web review completes, so complete Web review before `/loopora-run`. Otherwise report the returned Loop preview URL and the `ready_review_projection` summary when present: Loopora fit, fake-done risks, evidence expectations, coverage targets, judgment projection, and closure gate. If the preview is ready, report `review_before_loop`, `ready_next_step`, and the same-session run command as `ready_slash_command` plus fallback `ready_cli_command` when present. If the current user request explicitly confirms the preview or asks this Agent session to run both Loopora phases, continue after the summary by invoking `/loopora-run` or `ready_cli_command` in this same Agent session. Otherwise tell the user to confirm that review summary and preview URL before running `/loopora-run`; do not start the run from Web. If validation fails, report the Loopora error and repair the plan file before trying again.

## Boundaries

- `/loopora-plan` never starts a run.
- READY is decided by Loopora Core validation, not by {adapter_label} prose.
- If the task does not need a long-running evidence-governed Loop, explain that before generating.
- If judgment is missing, do not fill it with generic best practices; ask the user or return the Web review prefill.
- If `loopora agent {adapter} plan` returns a Web review URL instead of a ready preview, tell the user it needs Web review or more Loop setup before `/loopora-run`.
- Do not use expert commands such as `loopora spec`, `loopora bundles`, or `loopora loops create` as a substitute for `/loopora-plan` plus `/loopora-run` in this managed Agent entry.

## Candidate Bundle Skeleton

Use this schema scaffold when authoring a candidate file. Replace placeholder prose with task-specific content, but keep the object/list shape. Keep the two short anchor lines shown below on one physical line each; do not wrap them across newlines:

```yaml
version: 1
metadata:
  name: "task-specific-name"
  description: "task-specific description"
collaboration_summary: |
  This task needs multi-round Loopora governance because later Builder, Inspector, and GateKeeper rounds add evidence, handoffs, and final judgment beyond one Agent pass.
  Buckets: Proven, Weak, Unproven, Blocking, Residual risk.
loop:
  name: "task-specific-name"
  workdir: "/absolute/project/path"
  completion_mode: "gatekeeper"
  executor_kind: "{adapter}"
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
    ...
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
    {AGENT_PLAN_RESIDUAL_RISK_SKELETON_GUIDANCE}
    # Residual Risk
    - Accepted residual risk: ...
      Owner: ...
      Follow-up: ...
      Acceptance path: ...
    - Fail closed if: ...
role_definitions:
  - key: "task-builder"
    name: "Task Builder"
    description: "Implements the narrow task and produces durable proof."
    archetype: "builder"
    prompt_ref: "task-builder.md"
    prompt_markdown: |
      ---
      version: 1
      archetype: builder
      ---
      Task-specific Builder instructions.
    posture_notes: "Task-specific Builder evidence posture."
    executor_kind: "{adapter}"
    executor_mode: "preset"
    command_cli: ""
    command_args_text: ""
    model: ""
    reasoning_effort: ""
  - key: "task-inspector"
    name: "Task Inspector"
    description: "Re-reads Builder artifacts and classifies evidence before GateKeeper closure."
    archetype: "inspector"
    prompt_ref: "task-inspector.md"
    prompt_markdown: |
      ---
      version: 1
      archetype: inspector
      ---
      Task-specific Inspector instructions.
      First inspect Builder handoffs and cited task-owned artifacts. Reuse fresh complete successful proof artifacts as primary evidence; run new commands only for missing, stale, ambiguous, conflicting, or distinct uncovered evidence gaps.
      Buckets: Proven, Weak, Unproven, Blocking, Residual risk.
    posture_notes: "Task-specific Inspector evidence classification posture. Inspect Builder artifacts first; rerun proof only for missing, stale, ambiguous, conflicting, or distinct uncovered gaps. Buckets: Proven, Weak, Unproven, Blocking, Residual risk."
    executor_kind: "{adapter}"
    executor_mode: "preset"
    command_cli: ""
    command_args_text: ""
    model: ""
    reasoning_effort: ""
  - key: "task-gatekeeper"
    name: "Task GateKeeper"
    description: "Verifies exact evidence and closes only when task proof is strong."
    archetype: "gatekeeper"
    prompt_ref: "task-gatekeeper.md"
    prompt_markdown: |
      ---
      version: 1
      archetype: gatekeeper
      ---
      Task-specific GateKeeper instructions.
      Inspect known upstream evidence refs, handoffs, and cited task-owned artifacts before running any new proof command. Pass only from exact supporting evidence refs.
      Buckets: Proven, Weak, Unproven, Blocking, Residual risk.
    posture_notes: "Task-specific GateKeeper closure posture. Buckets: Proven, Weak, Unproven, Blocking, Residual risk."
    executor_kind: "{adapter}"
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

`loop`, `spec`, and `workflow` must be objects, not lists. `workflow.steps` is the list of step objects. Each role definition must include `key`, `name`, `description`, `archetype`, `prompt_ref`, `prompt_markdown`, `posture_notes`, executor fields, `model`, and `reasoning_effort`. Default to Builder -> Inspector -> GateKeeper because semantic lint expects bucket projection to reach Inspector posture and GateKeeper closure. Use literal `prompt_markdown: |`; do not use folded `>-` because it collapses YAML front matter lines and fails validation.
"""


def agent_recovery_matrix() -> str:
    return """# Loopora Recovery Matrix

Read the returned JSON, even if the command exits nonzero. Do not pipe Loopora JSON, role wrappers, result wrappers, proof artifacts, or recovery payloads through `head`, `head -c`, `tail`, `sed`, Python string slicing, or other truncating filters; read the complete compact JSON, or redirect the complete JSON to a file and parse the top-level `summary`. Read the top-level `summary` first; old summary keys live only under `raw.legacy` as diagnostics. The summary is the compact decision before the full session/run payload, including `task_proven`, `task_outcome`, `lifecycle_vs_task`, continuation, and any terminal continuation command when the previous run lifecycle closed without task proof. If the payload has `ready: false` or `loop_recovery`, stop before dispatching any role agent.

- `loop_recovery=choose_recoverable_context`: this Agent session has no exact context card, but the workdir has recoverable Loopora contexts. Report `selection_hint`, runnable/non-runnable counts, and each visible `option_id`, `choice_status`, `choice_hint`, `runnable`, linked run status, terminal `task_verdict_status` / `task_verdict_summary` when present, runnable choices' `next_command` / `next_slash_command` and `next_cli_command`, non-runnable choices' `preview_path`, `validation_error`, `repair_focus`, and `next_plan_command` when present, run/session summary, and Web URL if present. Do not guess.
- `loop_recovery=plan_first`: this Agent session/workdir has no ready Loop preview or recoverable run context. Report `required_inputs`, `ask_user`, one main-session `question_action`, `recommended_reply_shape`, `decision_impact`, `example_user_reply`, `message_source_policy`, `message_cli_command`, and `next_plan_command`; keep `task_message_template`, `first_task_message_example`, and `debug_cli_example_command` as diagnostics below the first screen. Use the host's official user-question or follow-up capability when needed, but if the current host prompt already contains the task goal, fake-done risk, required evidence, and judgment tradeoffs, put that prompt into `message_cli_command` and rerun `/loopora-plan --message` directly. If the answer is only a rough goal, return Web review prefill or ask one main-session follow-up rather than synthesizing a READY candidate. Do not create a plan implicitly from `/loopora-run`.
- `loop_recovery=active_run_conflict`: another active Loopora run already owns this workdir. Report the active run id/status/current step, continue it with `next_active_run_command`, or ask before stopping it; do not start a second run in the same workdir.
- `loop_recovery=finish_web_review`: the current `/loopora-plan` result needs Web review before `/loopora-run`. Report `preview_url`, `requires_web_alignment`, `loopora_fit_contradiction`, `review_status`, `review_focus`, `run_blocked_until_web_review`, `after_review_cli_command_status`, `after_review_ready`, `after_web_review_cli_command`, and `after_review_command`, and do not run those commands until Web review completes.
- `loop_recovery=repair_candidate_plan_file`: the candidate plan file failed validation. Report the source plan, preview copy, validation error, repair_task_message, repair focus, repair_cli_command_policy, repair_reference, and next_repair_step. Repair the plan file directly so it preserves repair_task_message and repair_focus in spec, roles, workflow, and evidence rules; do not inspect Loopora source/help output, run `which loopora`, run `loopora diagnose`, search examples, or run filesystem-wide discovery such as `find /`; rerun `/loopora-plan`, and only then rerun `/loopora-run`.
- `loop_recovery=preview_not_ready`: the associated preview is not ready; return to `/loopora-plan` or Web review.
- `loop_recovery=repair_context_card`: the local Agent context card is unreadable or invalid. Report the context-card path, run `loopora init <adapter> --check --workdir "$PWD"` for diagnosis, and use `/loopora-plan fresh` only if the user wants a new Loop.

Do not collapse these recovery states into a generic "run /loopora-plan first" message, and do not create a new plan implicitly from `/loopora-run`.
"""


def agent_result_template_guide(adapter: str) -> str:
    return f"""# Loopora Result Template Guide

In the main Agent/Orchestrator session, open the result template from `next_step.submit_hint.result_template_absolute_path` or `next_step.submit_hint.result_template_path`. Do not hand-write the wrapper from memory.

The template has three top-level blocks:

```json
{{
  "loopora_host_dispatch": {{ "...": "pre-filled native dispatch proof" }},
  "loopora_result_contract": {{ "...": "ignored on submit; use as the local fill guide" }},
  "result": {{ "...": null }}
}}
```

Read `loopora_result_contract.step_id`, `.role`, `.action_policy`, `.required_coverage`, `.known_evidence_ids`, `.evidence_ref_contract`, `.evidence_rules`, `.role_dispatch`, `.native_todo`, `.native_trace_contract`, `.output_schema`, `.result_file_to_write`, and `.submit_command` before filling the file. Replace every `null` placeholder before submit, use empty arrays when the schema permits and there is no item to report, and remove optional placeholder fields you do not submit. The role agent returns raw wrapper JSON to the main session; the main session writes the result file and runs submit. The submitted filled file should contain exactly `loopora_host_dispatch` and `result`; use `loopora_result_contract` as the local template guide, then remove that helper block from the filled copy before submit.

If submit exits nonzero with `submit_repair=repair_result_json`, read the top-level `summary` first, report `repair_focus`, `result_file_to_repair`, `schema_lookup`, and `next_repair_step`; repair the filled copy and resubmit rather than continuing the run.

Preserve the template's `loopora_host_dispatch` except for `actual_agent` when the host-native role agent returned the same required target agent and a schema-shaped role output, and optional `native_trace` / `native_trace_ref` fields when the host exposes an official subagent/task trace. If the role call returns no wrapper or no structured output, stop before submit instead of constructing a role result from main-session observations. `target_agent` and `actual_agent` must both equal `next_step.role_dispatch.target_agent`, `inline` must be false, and `adapter` must be `{adapter}`.
"""


def agent_role_dispatch_guide(adapter: str) -> str:
    dispatch_guidance = agent_native_dispatch_guidance(adapter).strip()
    extra = f"\n\n{dispatch_guidance}" if dispatch_guidance else ""
    return f"""# Loopora Role Dispatch Guide

Act as the Loopora Orchestrator. Do not perform role work inline. Read `next_step.role_dispatch.target_agent` and invoke that exact host-native role agent or task agent:

- builder step -> `loopora-builder`
- inspector/custom step -> `loopora-inspector`
- gatekeeper step -> `loopora-gatekeeper`
- guide step -> `loopora-guide`

Before dispatch, check `next_step.role_dispatch.target_agent_config_exists`. If it is false, stop and report that the target agent config is missing, then run `loopora agent {adapter} check --workdir "$PWD"` and repair with `loopora init {adapter} --workdir "$PWD"` before trying to submit role evidence.

Pass `summary.next_role_dispatch_message` or `summary.next_step.role_dispatch_message` verbatim as the whole role prompt when present. For Claude Agent/Task or any host role tool with a `prompt` input, that prompt input itself must be the compact dispatch message and must start with `Use this exact string as the whole Agent/Task prompt`; put target-role selection in the tool's agent/subagent field or short description, not in the prompt body. Do not add wrapper framing before or after it, even one sentence. Never prepend `You are running as`, append `Do the following:`, rewrite anchors as `target_agent:`, expand it with your own role playbook, schemas, evidence ledgers, copied run payload, or examples, or append extra paragraphs after the compact message. If that field is absent, build a compact role-dispatch message that names `next_step.role_dispatch.target_agent`, the StepInstruction context path, the step-contract path, the result-template path, and short navigation anchors such as coverage target IDs, action policy, required coverage status, known evidence IDs, and relevant artifact paths. The role agent must open the local context/step-contract/template paths for the full prompt, output schema, judgment contract, evidence rules, and known evidence details. Ask the role agent to return one raw JSON object only, with no Markdown fence, prose preface, code block, or trailing explanation. Do not paste full CLI JSON, full run payloads, large file contents, unrelated transcript history, full schemas, full evidence ledger rows, or hand-written result-wrapper examples into the role prompt.

Ask the role agent to return one raw JSON object only to the main Agent session, with no Markdown fence, prose preface, code block, or trailing explanation. Tell the role agent that any result-template outbox path, `result_file_to_write`, or submit command is for the main session only. The main Agent session writes the Loopora result file and submits it; do not ask read-only role agents to save Loopora outbox result files or to use Bash/Write as a fallback writer.

Use the host's official todo/progress-list capability when available to create or update `next_step.native_todo`. Treat that todo list as user-visible progress only, never as evidence. If the host exposes an official subagent/task trace id or tool-call id, carry it into `loopora_host_dispatch.native_trace` or `native_trace_ref`; do not invent trace ids.

If the host cannot invoke the required role agent, or the role call returns no wrapper / no structured output, stop and report that native dispatch is unavailable rather than submitting inline work.{extra}
"""
