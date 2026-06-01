from __future__ import annotations

from loopora.agent_adapter_entry_sections import AdapterEntrySection, render_adapter_entry_sections
from loopora.agent_adapter_role_contracts import agent_native_dispatch_guidance
from loopora.agent_native_adapter_contracts import (
    NATIVE_RUN_ENTRY_CONTRACT_BULLETS,
    NATIVE_RUN_ENTRY_CONTRACT_TITLE,
)


def _agent_run_sections(*, adapter: str, marker_source: str, context_bits: str) -> list[AdapterEntrySection]:
    return [
        AdapterEntrySection(
            "Purpose",
            "Start, resume, or continue evidence collection for the reviewed Loop preview bound to this Agent session or workdir.",
        ),
        AdapterEntrySection(
            "Run Command",
            (
                f"`LOOPORA_AGENT_ENTRY_SOURCE={marker_source} loopora agent {adapter} run --workdir \"$PWD\"{context_bits} "
                f"--entry-source {marker_source} --json`"
            ),
        ),
        AdapterEntrySection(
            "Recovery",
            "If the command returns `ready: false` or `loop_recovery`, report that recovery path and stop before role dispatch.",
        ),
        AdapterEntrySection(
            "Work Panel Use",
            (
                "Read `agent_v3_envelope.summary.agent_work_panel` first. In the main Agent session, report "
                "`agent_work_panel:` before technical paths after `/loopora-run`, `loopora agent ... next`, and submit; "
                "include `state`, `next_action`, `evidence_focus`, and `todo_items` so the user sees the next move."
            ),
        ),
        AdapterEntrySection(
            "Role Dispatch",
            (
                "Invoke the exact host-native role agent named by `next_step.role_dispatch.target_agent`; never submit inline work "
                "as if a role agent ran."
            ),
        ),
        AdapterEntrySection(
            "Result Template",
            (
                "Open the active result template, preserve `loopora_host_dispatch`, fill only `result`, and submit the filled copy "
                "with the provided command."
            ),
        ),
        AdapterEntrySection(
            "Proof Boundary",
            "Loopora proof comes only from submitted evidence refs, coverage, and task verdict; todo, host status, and native trace are experience projections.",
        ),
        AdapterEntrySection(
            "Failure Modes",
            "If dispatch, schema, stale-step, or proof validation blocks submit, report the typed repair envelope and stop before inline fallback.",
        ),
    ]


def agent_run_section_overview(*, adapter: str, marker_source: str, context_bits: str) -> str:
    return render_adapter_entry_sections(
        _agent_run_sections(adapter=adapter, marker_source=marker_source, context_bits=context_bits)
    )


def agent_native_loop_body(*, adapter: str, marker_source: str, context_arg: str = "") -> str:
    context_bits = f" {context_arg}" if context_arg else ""
    dispatch_guidance = agent_native_dispatch_guidance(adapter)
    section_overview = agent_run_section_overview(adapter=adapter, marker_source=marker_source, context_bits=context_bits)
    return f"""# Loopora Run Contract

{section_overview}

## Detailed Contract

Enter Loopora's run stage. Start, resume, or continue evidence collection for the reviewed Loop preview associated with this session or workdir.

Use this entry when the user says to run, resume, continue, keep going, close evidence gaps, or perform the next proof pass for the current Loop. If the user asks to change the judgment structure, evidence requirements, GateKeeper strictness, role responsibilities, workflow shape, or plan repair direction, stop and tell them to use `/loopora-plan` or Web review first. Do not silently rewrite the Loop from `/loopora-run`.

## Required path

1. Run:

```bash
LOOPORA_AGENT_ENTRY_SOURCE={marker_source} loopora agent {adapter} run --workdir "$PWD"{context_bits} --entry-source {marker_source} --json
```

If the user supplied `option:<id>`, add `--source-option-id <id>` to that command.

2. Read the returned JSON, even if the command exits nonzero. If the payload has `ready: false` or `loop_recovery`, stop before dispatching any role agent:
   - `loop_recovery=choose_recoverable_context` means this Agent session has no exact context card, but the workdir has one or more recoverable Agent Runner Loops. Report `selection_hint`, runnable/non-runnable counts, and the choices with `choice_status`, `choice_hint`, `runnable`, linked run status, and terminal `task_verdict_status` / `task_verdict_summary` when present; for runnable choices include `next_command` / `next_slash_command` and `next_cli_command`, include `next_agent_command` when the recovery came from `loopora agent {adapter} next`, and for non-runnable choices include `preview_path`, `validation_error`, `repair_focus`, and `next_plan_command` when present; then ask the user to pick in Web or start fresh with `/loopora-plan`; do not guess which old Loop they meant.
   - `loop_recovery=plan_first` means this Agent session/workdir has no ready Loop preview or recoverable run context. Report `required_inputs`, `ask_user`, one main-session `question_action`, `recommended_reply_shape`, `decision_impact`, `example_user_reply`, and `next_plan_command`; keep `task_message_template`, `first_task_message_example`, and `debug_cli_example_command` as diagnostics below the first screen. Use the host's official user-question or follow-up capability when available to ask one Loop-shaping question for the task goal, fake-done risk, required evidence, and judgment tradeoffs, then put the user's answer into `/loopora-plan --message`; if the answer is only a rough goal, return Web review prefill or ask one main-session follow-up rather than synthesizing a READY candidate. Do not create a plan implicitly from `/loopora-run`.
   - `loop_recovery=active_run_conflict` means another active Loopora run already owns this workdir. Report the active run id/status/current step, continue it with `next_active_run_command`, or ask before stopping it; do not start a second run in the same workdir.
   - `loop_recovery=finish_web_review` means the current `/loopora-plan` result needs Web review before `/loopora-run`; report `preview_url`, `requires_web_alignment`, `loopora_fit_contradiction`, `review_status`, `review_focus`, `after_review_ready`, and `after_review_command` instead of starting work.
   - `loop_recovery=repair_candidate_plan_file` means the candidate plan file failed validation; report `preview_url`, `requires_candidate_repair`, `loopora_fit_contradiction`, `repair_task_message`, the source plan / preview copy paths from the context card or session, and the validation / repair focus. Tell the user to repair the plan file so it preserves `repair_task_message` and `repair_focus` in spec, roles, workflow, and evidence rules, rerun `/loopora-plan`, and only then rerun `/loopora-run`.
   - `loop_recovery=preview_not_ready` means the associated preview is not ready; return to `/loopora-plan` or Web review.
   - `loop_recovery=repair_context_card` means the local context card is unreadable or invalid. Run `loopora init {adapter} --check --workdir "$PWD"` to diagnose, then either repair the file or use `/loopora-plan fresh` if the user wants a new Loop.
   Do not collapse these recovery states into a generic “run /loopora-plan first” message, and do not create a new plan implicitly from `/loopora-run`.
3. For a runnable payload, read root `agent_v3_envelope.summary` first, then `summary.agent_work_panel`, `run_url`, run-level `judgment_contract`, and, unless the run is already complete, `next_step` with its own `next_step.judgment_contract` projection. In the main Agent session, report `agent_work_panel:` first with `state`, `next_action`, `evidence_focus`, and `todo_items`; put step contract path, result template, submit command, and other technical handoff below that first-screen panel. If you used `loopora agent {adapter} next`, the same envelope has `kind=agent_next`; if it returns recovery, report that recovery summary and use `next_agent_command` for the already-active run rather than creating a new plan. Treat `summary.task_proven`, `summary.task_outcome`, and `summary.lifecycle_vs_task` as the compact task-proof answer, separate from the run lifecycle. If `next_step.native_todo` is present and the host has an official todo/progress-list capability, create or update those todo items as live progress; do not cite the todo list as evidence. If `summary.next_step.iteration_repair.active` is true, report the source step, blocking items, evidence refs, top gaps, and recommended next action before invoking the next role. If `summary.continuation.active` is true, report the previous run id, previous task verdict status, missing check count, and next focus before invoking the next role. If `complete` is true and `task_next_action.kind` is `continue_evidence` or `summary.task_proven` is false, the run lifecycle is complete but the task is not proven; do not summarize the task as done. If `complete` is true and `task_next_action.kind` is `already_passed` or `summary.task_proven` is true, no new role dispatch or evidence pass starts unless the task scope changes.
4. Act as the Loopora Orchestrator. Do not perform role work inline. Read `next_step.role_dispatch.target_agent` and invoke that exact host-native role agent / task agent through the host's official mechanism:
   - builder step -> `loopora-builder`
   - inspector/custom step -> `loopora-inspector`
   - gatekeeper step -> `loopora-gatekeeper`
   - guide step -> `loopora-guide`
{dispatch_guidance.rstrip()}
   Host auto-activation, compatibility-layer routing, or rule injection may help the surrounding context, but they are not Loopora dispatch proof. Use the exact `role_dispatch.target_agent`, and only set `loopora_host_dispatch.actual_agent` when the host invoked that same Loopora role agent.
5. Pass the full `next_step.prompt`, `next_step.judgment_contract`, `next_step.required_coverage`, `next_step.output_schema`, `next_step.action_policy`, `next_step.known_evidence_ids`, `next_step.known_evidence_refs`, and the StepInstruction context refs (`next_step.context_path` and `next_step.context_absolute_path`) to the target role agent. Do not summarize, trim, or rewrite the prompt or judgment projection; they contain the frozen run contract, StepInstruction context, evidence rules, and output instructions.
6. Treat `next_step.judgment_contract`, `next_step.output_schema`, `next_step.action_policy`, `next_step.evidence_rules`, `next_step.evidence_ref_contract`, `next_step.known_evidence_ids`, `next_step.known_evidence_refs`, `next_step.native_todo`, and `next_step.role_dispatch` as the immutable step contract. If `next_step.role_dispatch.target_agent_config_exists` is false, run `loopora agent {adapter} check --workdir "$PWD"` and repair with `loopora init {adapter} --workdir "$PWD"` before dispatch. If the host cannot invoke the required role agent, stop and report that native dispatch is unavailable rather than submitting inline work. Do not copy credentials, API keys, tokens, or environment secrets into role output, result files, native traces, or evidence notes; cite redacted files, command events, or stable evidence ids instead.
7. Open the result template from `next_step.submit_hint.result_template_absolute_path` or `next_step.submit_hint.result_template_path`. Do not hand-write the wrapper from memory. The template is the white-box handoff file for this step:

```json
{{
  "loopora_host_dispatch": {{ "...": "pre-filled native dispatch proof" }},
  "loopora_result_contract": {{ "...": "ignored on submit; use as the local fill guide" }},
  "result": {{ "...": null }}
}}
```

Read `loopora_result_contract.step_id`, `.role`, `.action_policy`, `.required_coverage`, `.known_evidence_ids`, `.evidence_ref_contract`, `.evidence_rules`, `.role_dispatch`, `.native_todo`, `.native_trace_contract`, `.output_schema`, `.result_file_to_write`, and `.submit_command` before filling the file. The template's `result` is a schema-shaped scaffold with invalid `null` placeholders. Replace every placeholder before submit, use empty arrays when the schema permits and there is no item to report, and remove optional placeholder fields you do not submit. The helper block is ignored by Loopora submit, so it may remain in the filled wrapper; never copy helper fields into `result`.

8. Save a filled copy to `next_step.submit_hint.result_file_absolute_path` / `result_file_path` when present, or otherwise under `next_step.submit_hint.result_outbox_absolute_dir` / `result_outbox_dir`, keeping the template available for audit. Preserve the template's `loopora_host_dispatch` exactly except for setting `actual_agent` only if the host-native role agent returned the same required target agent, and filling optional `native_trace` / `native_trace_ref` fields when the host exposes an official subagent/task trace. Fill only the `result` object with the role agent output. The resulting wrapper should still have this shape:

```json
{{
  "loopora_host_dispatch": {{
    "schema_version": 1,
    "adapter": "{adapter}",
    "run_id": "<run-id>",
    "iter": 0,
    "step_id": "<step-id>",
    "step_order": 0,
    "target_agent": "<next_step.role_dispatch.target_agent>",
    "actual_agent": "<same exact agent name>",
    "dispatch_mode": "host_subagent",
    "inline": false,
    "native_tool_name": "<official host tool name when available>",
    "native_trace_ref": "<official host trace id when available>",
    "native_trace": {{"available": false}},
    "attestation": "The host invoked the named Loopora role agent for this step."
  }},
  "loopora_result_contract": {{ "...": "optional helper copied from the template; ignored on submit" }},
  "result": {{ "...": "must match next_step.output_schema exactly" }}
}}
```

For GateKeeper, `result` means `passed`, `decision_summary`, `evidence_refs`, and the other schema fields, not a `verdict` / `task_verdict` envelope. Any `evidence_refs` list must contain only exact IDs copied from the template's `loopora_result_contract.known_evidence_ids`; never create derived IDs such as `<known-id>_binding` or `<known-id>_output`.

9. Submit with `next_step.submit_hint.command`; current templates point this command at the recommended filled result file path, and older templates may require replacing `RESULT_JSON_PATH` with the filled result file path. If the command is unavailable, use the equivalent command below with the same `LOOPORA_AGENT_ENTRY_SOURCE` and `--entry-source` markers:

```bash
LOOPORA_AGENT_ENTRY_SOURCE={marker_source} loopora agent {adapter} submit --workdir "$PWD"{context_bits} --run-id <run-id> --step-id <step-id> --result-file RESULT_JSON_PATH --entry-source {marker_source} --json
```

10. Read the submit response JSON, even if the command exits nonzero. Read root `agent_v3_envelope.summary` first; report `summary.agent_work_panel` as `agent_work_panel:` in the main Agent session before technical handoff, and use `summary.task_proven`, `summary.task_outcome`, and `summary.lifecycle_vs_task` to separate role submit success from task proof. On a successful submit, report `submitted_step.step_id`, `submitted_step.evidence_refs`, and `submitted_step.handoff_absolute_path` as the evidence anchor that was just added to the run; when `submitted_step.status` is blocked, also report `submitted_step.blocking_items` and `submitted_step.recommended_next_action`. If it returns `submit_repair=repair_result_json`, report `repair_focus`, `result_file_to_repair`, `schema_lookup`, and `next_repair_step` from the same summary; repair the filled copy and resubmit before continuing. If the submit response returns another `next_step`, repeat native role dispatch, template fill, and submit. When `complete` is true, inspect `run.task_verdict.status`, `summary.task_proven`, and any `task_next_action` before deciding what to report:
   - If the verdict is `passed` or `passed_with_residual_risk`, stop and report `run.run_status`, `run.task_verdict`, and `judgment_contract` separately.
   - If `task_next_action.kind` is `continue_evidence`, stop this run's role dispatch loop, but do not report the task as complete. Report `run.run_status`, `run.task_verdict`, `task_next_action.next_loop_command`, `task_next_action.guidance`, and any `task_next_action.task_verdict_summary`; tell the user that running `/loopora-run` again in the same Agent session starts the next evidence pass with the previous verdict and coverage gaps.
   - If `task_next_action.kind` is `already_passed`, stop without dispatching role work and report `run.run_status`, `run.task_verdict`, `task_next_action.guidance`, and any `task_next_action.task_verdict_summary`; tell the user that no new evidence pass starts unless the scope changes.
   - If the verdict is anything else non-passing, fail closed: report the lifecycle/verdict split and ask the user to continue with `/loopora-run` or adjust the Loop from the run URL instead of claiming success.

Copy the Loopora commands with `LOOPORA_AGENT_ENTRY_SOURCE` and `--entry-source`; those markers prove this run came from the Loopora-managed Agent entry.

## Boundaries

- If the command says no Loop preview is associated with this session/workdir, tell the user to run `/loopora-plan` first.
- If the command returns `loop_recovery`, report that recovery path and stop; do not proceed to role dispatch.
- Do not create a bundle implicitly from `/loopora-run`.
- Do not bypass Loopora's bundle import, run lifecycle, evidence ledger, or GateKeeper verdict.
- Do not launch `codex`, `claude`, or `opencode` from inside this entry. The current host Agent must dispatch to the named host-native Loopora role agent and submit wrapper JSON to Loopora.
- Do not treat host auto-activation, compatibility-layer routing, or injected rules as proof that the required Loopora role agent ran.
- Do not copy credentials, API keys, tokens, or environment secrets into Loopora result files or evidence notes.
"""


def agent_native_run_entry_contract() -> str:
    bullets = "\n".join(f"- {item}" for item in NATIVE_RUN_ENTRY_CONTRACT_BULLETS)
    return f"## {NATIVE_RUN_ENTRY_CONTRACT_TITLE}\n\n{bullets}\n"
