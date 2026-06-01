from __future__ import annotations

from loopora.agent_adapter_entry_sections import AdapterEntrySection, render_adapter_entry_sections
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
                f"--message \"<non-empty short task summary>\" --bundle-file <candidate-plan-file> --entry-source {marker_source}`"
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
            "Read `agent_v3_envelope.summary` before raw legacy diagnostics and keep diagnostics below the first screen.",
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
            "READY is decided by Loopora Core validation. Host prose, todo completion, and native traces are not Loopora proof.",
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
{argument_text}
## Required path

1. Summarize the current task, workdir, constraints, Loopora fit, local governance files, fake-done risks, evidence expectations, execution strategy, judgment tradeoffs, and residual-risk policy from the current {adapter_label} context. Loopora fit must say why one Agent pass, one review, direct chat / direct answer, one-off task handling, or benchmark/test-harness-only validation is not enough, and what later rounds will add as new evidence, handoffs, or a GateKeeper verdict. If `AGENTS.md`, `design/README.md`, `design/`, or `tests/` matter, compile them into Builder reading, Inspector / Custom verification, and GateKeeper Weak / Unproven / Blocking responsibility rather than a marker list. Execution strategy must say what to build, prove, repair, narrow, expand, or defer first; residual risk must name what can be accepted plus an owner, follow-up, or acceptance path, or say the task fails closed. Preserve task-specific categories such as notification, audit, permission, payment, export, browser journey, command evidence, owner, follow-up, and acceptance path; do not let a bundle pass merely because it repeats one or two object words from the task.
2. Check Loopora fit and judgment sufficiency before authoring a Loop plan file. If Loopora fit is false or a missing human decision would change the Loop shape, ask one focused question; if the host cannot continue that conversation, call `loopora agent {adapter} plan` with `--message "<non-empty short task summary>"` but without `--bundle-file` to return a Web review prefill. When retrying from the user's answer, put that answer into `--message`; if the answer is only a rough goal without fake-done risk, evidence, or judgment tradeoff signal, ask one main-session follow-up or return a Web review prefill instead of synthesizing a complete READY candidate. Do not invent human judgment just to pass validation.
3. Create a complete Loopora `version: 1` candidate plan file for that task. The plan file must express `spec`, `role_definitions`, `workflow`, evidence flow, and a GateKeeper finish step. Preserve the current task's Loopora fit reason, high-signal objects, success outcome categories, fake-done risk categories, concrete evidence modes, execution priorities, judgment tradeoffs, local governance responsibilities, and risk terms in the runnable surfaces, not only in the short CLI summary. If the current task explicitly provides a candidate plan file path, submit that file instead of reauthoring it.
4. Save a newly authored candidate plan file to a temporary file under `.loopora/agent_inbox/{adapter}/`; if a candidate path was explicitly provided, use that path.
5. Run:

```bash
LOOPORA_AGENT_ENTRY_SOURCE={marker_source} loopora agent {adapter} plan --workdir "$PWD"{context_bits} --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source {marker_source}
```

6. Read the returned JSON or plain output even if the command exits nonzero. For JSON, read root `agent_v3_envelope.summary` first; old summary keys live only under `raw.legacy` as diagnostics. The summary is the compact planning decision before the full session payload, including the agent surface summary so the host can confirm `/loopora-plan` and `/loopora-run` are project-local Agent entries, role dispatch is host-native, and nested provider CLIs are not used. If it returns `loop_recovery=plan_message_required`, report one Loop-shaping question from `ask_user` / `question_action`, the `recommended_reply_shape`, `decision_impact`, `example_user_reply`, and `next_plan_command`; use the host's official user-question or follow-up capability when available to ask in the main Agent session before retrying, and keep `task_message_template`, `first_task_message_example`, and `debug_cli_example_command` as JSON diagnostics only; do not invent a summary. If it returns `loop_recovery=repair_candidate_plan_file`, report `plan_file_to_repair`, `preview_plan_copy`, `validation_error`, `repair_task_message`, `repair_focus`, `repair_slash_command`, and `repair_cli_command`; repair the candidate plan so it preserves `repair_task_message` and `repair_focus` in spec, roles, workflow, and evidence rules, then rerun `/loopora-plan` with the repaired file before `/loopora-run`. If it returns `loop_recovery=finish_web_review`, report the preview URL, `review_status`, `review_focus`, `after_review_ready`, `after_review_slash_command`, `after_review_cli_command`, and legacy `after_review_command`, then complete Web review before `/loopora-run`. Otherwise report the returned Loop preview URL and the `ready_review_projection` summary when present: Loopora fit, fake-done risks, evidence expectations, coverage targets, judgment projection, and closure gate. If the preview is ready, report `review_before_loop`, `ready_next_step`, and the same-session run command as `ready_slash_command` plus fallback `ready_cli_command` when present, tell the user to confirm that review summary and preview URL, then run `/loopora-run` in this same Agent session; do not start the run from Web. If validation fails, report the Loopora error and repair the plan file before trying again.

## Boundaries

- `/loopora-plan` never starts a run.
- READY is decided by Loopora Core validation, not by {adapter_label} prose.
- If the task does not need a long-running evidence-governed Loop, explain that before generating.
- If judgment is missing, do not fill it with generic best practices; ask the user or return the Web review prefill.
- If `loopora agent {adapter} plan` returns a Web review URL instead of a ready preview, tell the user it needs Web review or more Loop setup before `/loopora-run`.
"""


def agent_recovery_matrix() -> str:
    return """# Loopora Recovery Matrix

Read the returned JSON, even if the command exits nonzero. Read root `agent_v3_envelope.summary` first; old summary keys live only under `raw.legacy` as diagnostics. The summary is the compact decision before the full session/run payload, including `task_proven`, `task_outcome`, `lifecycle_vs_task`, continuation, and any terminal continuation command when the previous run lifecycle closed without task proof. If the payload has `ready: false` or `loop_recovery`, stop before dispatching any role agent.

- `loop_recovery=choose_recoverable_context`: this Agent session has no exact context card, but the workdir has recoverable Loopora contexts. Report `selection_hint`, runnable/non-runnable counts, and each visible `option_id`, `choice_status`, `choice_hint`, `runnable`, linked run status, terminal `task_verdict_status` / `task_verdict_summary` when present, runnable choices' `next_command` / `next_slash_command` and `next_cli_command`, non-runnable choices' `preview_path`, `validation_error`, `repair_focus`, and `next_plan_command` when present, run/session summary, and Web URL if present. Do not guess.
- `loop_recovery=plan_first`: this Agent session/workdir has no ready Loop preview or recoverable run context. Report `required_inputs`, `ask_user`, one main-session `question_action`, `recommended_reply_shape`, `decision_impact`, `example_user_reply`, and `next_plan_command`; keep `task_message_template`, `first_task_message_example`, and `debug_cli_example_command` as diagnostics below the first screen. Use the host's official user-question or follow-up capability when available to ask one Loop-shaping question for the task goal, fake-done risk, required evidence, and judgment tradeoffs, then put the user's answer into `/loopora-plan --message`; if the answer is only a rough goal, return Web review prefill or ask one main-session follow-up rather than synthesizing a READY candidate. Do not create a plan implicitly from `/loopora-run`.
- `loop_recovery=active_run_conflict`: another active Loopora run already owns this workdir. Report the active run id/status/current step, continue it with `next_active_run_command`, or ask before stopping it; do not start a second run in the same workdir.
- `loop_recovery=finish_web_review`: the current `/loopora-plan` result needs Web review before `/loopora-run`. Report `preview_url`, `requires_web_alignment`, `loopora_fit_contradiction`, `review_status`, `review_focus`, `after_review_ready`, and `after_review_command`.
- `loop_recovery=repair_candidate_plan_file`: the candidate plan file failed validation. Report the source plan, preview copy, validation error, repair_task_message, and repair focus. Tell the user to repair the plan file so it preserves repair_task_message and repair_focus in spec, roles, workflow, and evidence rules, rerun `/loopora-plan`, and only then rerun `/loopora-run`.
- `loop_recovery=preview_not_ready`: the associated preview is not ready; return to `/loopora-plan` or Web review.
- `loop_recovery=repair_context_card`: the local Agent context card is unreadable or invalid. Report the context-card path, run `loopora init <adapter> --check --workdir "$PWD"` for diagnosis, and use `/loopora-plan fresh` only if the user wants a new Loop.

Do not collapse these recovery states into a generic "run /loopora-plan first" message, and do not create a new plan implicitly from `/loopora-run`.
"""


def agent_result_template_guide(adapter: str) -> str:
    return f"""# Loopora Result Template Guide

Open the result template from `next_step.submit_hint.result_template_absolute_path` or `next_step.submit_hint.result_template_path`. Do not hand-write the wrapper from memory.

The template has three top-level blocks:

```json
{{
  "loopora_host_dispatch": {{ "...": "pre-filled native dispatch proof" }},
  "loopora_result_contract": {{ "...": "ignored on submit; use as the local fill guide" }},
  "result": {{ "...": null }}
}}
```

Read `loopora_result_contract.step_id`, `.role`, `.action_policy`, `.required_coverage`, `.known_evidence_ids`, `.evidence_ref_contract`, `.evidence_rules`, `.role_dispatch`, `.native_todo`, `.native_trace_contract`, `.output_schema`, `.result_file_to_write`, and `.submit_command` before filling the file. Replace every `null` placeholder before submit, use empty arrays when the schema permits and there is no item to report, and remove optional placeholder fields you do not submit.

If submit exits nonzero with `submit_repair=repair_result_json`, read `agent_v3_envelope.summary` first, report `repair_focus`, `result_file_to_repair`, `schema_lookup`, and `next_repair_step`; repair the filled copy and resubmit rather than continuing the run.

Preserve the template's `loopora_host_dispatch` except for `actual_agent` when the host-native role agent returned the same required target agent, and optional `native_trace` / `native_trace_ref` fields when the host exposes an official subagent/task trace. `target_agent` and `actual_agent` must both equal `next_step.role_dispatch.target_agent`, `inline` must be false, and `adapter` must be `{adapter}`.
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

Pass the full `next_step.prompt`, `next_step.judgment_contract`, `next_step.required_coverage`, `next_step.output_schema`, `next_step.action_policy`, `next_step.known_evidence_ids`, `next_step.known_evidence_refs`, and the StepInstruction context refs (`next_step.context_path` and `next_step.context_absolute_path`) to the target role agent. Do not summarize, trim, or rewrite the prompt or judgment projection.

Use the host's official todo/progress-list capability when available to create or update `next_step.native_todo`. Treat that todo list as user-visible progress only, never as evidence. If the host exposes an official subagent/task trace id or tool-call id, carry it into `loopora_host_dispatch.native_trace` or `native_trace_ref`; do not invent trace ids.

If the host cannot invoke the required role agent, stop and report that native dispatch is unavailable rather than submitting inline work.{extra}
"""
