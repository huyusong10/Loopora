from __future__ import annotations

from dataclasses import dataclass

from loopora.agent_adapter_host_config import (
    CLAUDE_SESSION_HOOK_RELATIVE_PATH,
    claude_session_hook_script as _claude_session_hook_script,
)
from loopora.agent_adapter_role_contracts import (
    agent_native_dispatch_guidance,
    role_agent_body,
    role_agent_description,
)
from loopora.agent_native_adapter_contracts import (
    NATIVE_RUN_ENTRY_CONTRACT_BULLETS,
    NATIVE_RUN_ENTRY_CONTRACT_TITLE,
)
from loopora.service_types import LooporaError

ADAPTER_MANAGED_SCHEMA_VERSION = 3
ADAPTER_VERSION = 30
CODEX_ADAPTER_VERSION = ADAPTER_VERSION
CLAUDE_ADAPTER_VERSION = ADAPTER_VERSION
OPENCODE_ADAPTER_VERSION = ADAPTER_VERSION
CODEX_MANAGED_MARKER = "LOOPORA-MANAGED: codex-adapter"
CLAUDE_MANAGED_MARKER = "LOOPORA-MANAGED: claude-code-adapter"
OPENCODE_MANAGED_MARKER = "LOOPORA-MANAGED: opencode-adapter"
MANAGED_MARKERS = {
    "codex": CODEX_MANAGED_MARKER,
    "claude": CLAUDE_MANAGED_MARKER,
    "opencode": OPENCODE_MANAGED_MARKER,
}
MANAGED_MARKER = CODEX_MANAGED_MARKER


@dataclass(frozen=True, slots=True)
class AdapterEntrySection:
    title: str
    body: str


def _render_adapter_entry_sections(sections: list[AdapterEntrySection]) -> str:
    rendered: list[str] = []
    for section in sections:
        body = section.body.strip()
        if not body:
            continue
        rendered.append(f"## {section.title}\n\n{body}")
    return "\n\n".join(rendered).strip()


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


def _adapter_label(kind: str) -> str:
    return {
        "codex": "Codex",
        "claude": "Claude Code",
        "opencode": "OpenCode",
    }.get(kind, kind)


def managed_templates(kind: str) -> dict[str, str]:
    if kind == "codex":
        return _codex_managed_templates()
    if kind == "claude":
        return _claude_managed_templates()
    if kind == "opencode":
        return _opencode_managed_templates()
    raise LooporaError(f"{_adapter_label(kind)} adapter is not implemented yet")


def _codex_managed_templates() -> dict[str, str]:
    return {
        ".agents/skills/loopora-plan/SKILL.md": _codex_loopora_gen_skill(),
        ".agents/skills/loopora-plan/references/loopora-plan-contract.md": _agent_plan_contract("codex", "Codex", "codex_project_skill"),
        ".agents/skills/loopora-run/SKILL.md": _codex_loopora_loop_skill(),
        ".agents/skills/loopora-run/references/loopora-run-contract.md": _agent_native_loop_body(adapter="codex", marker_source="codex_project_skill"),
        ".agents/skills/loopora-run/references/loopora-recovery-matrix.md": _agent_recovery_matrix(),
        ".agents/skills/loopora-run/references/loopora-result-template-guide.md": _agent_result_template_guide("codex"),
        ".agents/skills/loopora-run/references/loopora-role-dispatch-guide.md": _agent_role_dispatch_guide("codex"),
        ".codex/agents/loopora-builder.toml": _codex_role_agent("builder"),
        ".codex/agents/loopora-inspector.toml": _codex_role_agent("inspector"),
        ".codex/agents/loopora-gatekeeper.toml": _codex_role_agent("gatekeeper"),
        ".codex/agents/loopora-guide.toml": _codex_role_agent("guide"),
        ".codex/agents/loopora-orchestrator.toml": _codex_role_agent("orchestrator"),
    }


def _claude_managed_templates() -> dict[str, str]:
    return {
        ".claude/skills/loopora-plan/SKILL.md": _claude_loopora_gen_skill(),
        ".claude/skills/loopora-plan/references/loopora-plan-contract.md": _agent_plan_contract("claude", "Claude Code", "claude_project_skill", context_arg='--context-id "${CLAUDE_SESSION_ID}"'),
        ".claude/skills/loopora-run/SKILL.md": _claude_loopora_loop_skill(),
        ".claude/skills/loopora-run/references/loopora-run-contract.md": _agent_native_loop_body(adapter="claude", marker_source="claude_project_skill", context_arg='--context-id "${CLAUDE_SESSION_ID}"'),
        ".claude/skills/loopora-run/references/loopora-recovery-matrix.md": _agent_recovery_matrix(),
        ".claude/skills/loopora-run/references/loopora-result-template-guide.md": _agent_result_template_guide("claude"),
        ".claude/skills/loopora-run/references/loopora-role-dispatch-guide.md": _agent_role_dispatch_guide("claude"),
        CLAUDE_SESSION_HOOK_RELATIVE_PATH: _claude_session_hook_script(
            marker=CLAUDE_MANAGED_MARKER,
            version=CLAUDE_ADAPTER_VERSION,
        ),
        ".claude/agents/loopora-builder.md": _claude_role_agent("builder"),
        ".claude/agents/loopora-inspector.md": _claude_role_agent("inspector"),
        ".claude/agents/loopora-gatekeeper.md": _claude_role_agent("gatekeeper"),
        ".claude/agents/loopora-guide.md": _claude_role_agent("guide"),
        ".claude/agents/loopora-orchestrator.md": _claude_role_agent("orchestrator"),
    }


def _opencode_managed_templates() -> dict[str, str]:
    return {
        ".opencode/commands/loopora-plan.md": _opencode_loopora_gen_command(),
        ".opencode/loopora/references/loopora-plan-contract.md": _agent_plan_contract("opencode", "OpenCode", "opencode_project_command", context_arg='--context-id "${OPENCODE_SESSION_ID:-}"', supports_arguments=True),
        ".opencode/commands/loopora-run.md": _opencode_loopora_loop_command(),
        ".opencode/loopora/references/loopora-run-contract.md": _agent_native_loop_body(adapter="opencode", marker_source="opencode_project_command", context_arg='--context-id "${OPENCODE_SESSION_ID:-}"'),
        ".opencode/loopora/references/loopora-recovery-matrix.md": _agent_recovery_matrix(),
        ".opencode/loopora/references/loopora-result-template-guide.md": _agent_result_template_guide("opencode"),
        ".opencode/loopora/references/loopora-role-dispatch-guide.md": _agent_role_dispatch_guide("opencode"),
        ".opencode/agents/loopora-builder.md": _opencode_role_agent("builder"),
        ".opencode/agents/loopora-inspector.md": _opencode_role_agent("inspector"),
        ".opencode/agents/loopora-gatekeeper.md": _opencode_role_agent("gatekeeper"),
        ".opencode/agents/loopora-guide.md": _opencode_role_agent("guide"),
        ".opencode/agents/loopora-orchestrator.md": _opencode_role_agent("orchestrator"),
    }


def _codex_role_agent(role: str) -> str:
    return f"""# {MANAGED_MARKER} version={CODEX_ADAPTER_VERSION} role={role}

name = "loopora-{role}"
description = "{role_agent_description(role)}"
developer_instructions = \"\"\"
{role_agent_body(role).rstrip()}
\"\"\"
"""


def _claude_role_frontmatter(role: str) -> str:
    if role == "orchestrator":
        return """tools: Agent, Task, Read, Write, Bash
maxTurns: 20"""
    if role == "builder":
        return """tools: Read, Glob, Grep, Bash, Write, Edit, MultiEdit
maxTurns: 20"""
    return """tools: Read, Glob, Grep, Bash
maxTurns: 12"""


def _claude_role_agent(role: str) -> str:
    return f"""---
name: loopora-{role}
description: "{role_agent_description(role)}"
{_claude_role_frontmatter(role)}
---

<!-- {CLAUDE_MANAGED_MARKER} version={CLAUDE_ADAPTER_VERSION} role={role} -->

# Loopora {role.capitalize() if role != "gatekeeper" else "GateKeeper"}

{role_agent_body(role)}
"""


def _opencode_role_frontmatter(role: str) -> str:
    if role == "orchestrator":
        return """mode: subagent
permission:
  task:
    "*": deny
    loopora-builder: allow
    loopora-inspector: allow
    loopora-gatekeeper: allow
    loopora-guide: allow"""
    return """mode: subagent
permission:
  task: deny"""


def _opencode_role_agent(role: str) -> str:
    return f"""---
description: "{role_agent_description(role)}"
{_opencode_role_frontmatter(role)}
---

<!-- {OPENCODE_MANAGED_MARKER} version={OPENCODE_ADAPTER_VERSION} role={role} -->

# Loopora {role.capitalize() if role != "gatekeeper" else "GateKeeper"}

{role_agent_body(role)}
"""


def _agent_plan_contract(
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
    section_overview = _render_adapter_entry_sections(_agent_plan_sections(adapter=adapter, marker_source=marker_source, context_bits=context_bits))
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


def _agent_recovery_matrix() -> str:
    return """# Loopora Recovery Matrix

Read the returned JSON, even if the command exits nonzero. Read root `agent_v3_envelope.summary` first; old summary keys live only under `raw.legacy` as diagnostics. The summary is the compact decision before the full session/run payload, including `task_proven`, `task_outcome`, `lifecycle_vs_task`, continuation, and any terminal continuation command when the previous run lifecycle closed without task proof. If the payload has `ready: false` or `loop_recovery`, stop before dispatching any role agent.

- `loop_recovery=choose_recoverable_context`: this Agent session has no exact context card, but the workdir has recoverable Agent Runner Loops. Report `selection_hint`, runnable/non-runnable counts, and each visible `option_id`, `choice_status`, `choice_hint`, `runnable`, linked run status, terminal `task_verdict_status` / `task_verdict_summary` when present, runnable choices' `next_command` / `next_slash_command` and `next_cli_command`, non-runnable choices' `preview_path`, `validation_error`, `repair_focus`, and `next_plan_command` when present, run/session summary, and Web URL if present. Do not guess.
- `loop_recovery=plan_first`: this Agent session/workdir has no ready Loop preview or recoverable run context. Report `required_inputs`, `ask_user`, one main-session `question_action`, `recommended_reply_shape`, `decision_impact`, `example_user_reply`, and `next_plan_command`; keep `task_message_template`, `first_task_message_example`, and `debug_cli_example_command` as diagnostics below the first screen. Use the host's official user-question or follow-up capability when available to ask one Loop-shaping question for the task goal, fake-done risk, required evidence, and judgment tradeoffs, then put the user's answer into `/loopora-plan --message`; if the answer is only a rough goal, return Web review prefill or ask one main-session follow-up rather than synthesizing a READY candidate. Do not create a plan implicitly from `/loopora-run`.
- `loop_recovery=active_run_conflict`: another active Loopora run already owns this workdir. Report the active run id/status/current step, continue it with `next_active_run_command`, or ask before stopping it; do not start a second run in the same workdir.
- `loop_recovery=finish_web_review`: the current `/loopora-plan` result needs Web review before `/loopora-run`. Report `preview_url`, `requires_web_alignment`, `loopora_fit_contradiction`, `review_status`, `review_focus`, `after_review_ready`, and `after_review_command`.
- `loop_recovery=repair_candidate_plan_file`: the candidate plan file failed validation. Report the source plan, preview copy, validation error, repair_task_message, and repair focus. Tell the user to repair the plan file so it preserves repair_task_message and repair_focus in spec, roles, workflow, and evidence rules, rerun `/loopora-plan`, and only then rerun `/loopora-run`.
- `loop_recovery=preview_not_ready`: the associated preview is not ready; return to `/loopora-plan` or Web review.
- `loop_recovery=repair_context_card`: the local Agent context card is unreadable or invalid. Report the context-card path, run `loopora init <adapter> --check --workdir "$PWD"` for diagnosis, and use `/loopora-plan fresh` only if the user wants a new Loop.

Do not collapse these recovery states into a generic "run /loopora-plan first" message, and do not create a new plan implicitly from `/loopora-run`.
"""


def _agent_result_template_guide(adapter: str) -> str:
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


def _agent_role_dispatch_guide(adapter: str) -> str:
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


def _agent_native_loop_body(*, adapter: str, marker_source: str, context_arg: str = "") -> str:
    context_bits = f" {context_arg}" if context_arg else ""
    dispatch_guidance = agent_native_dispatch_guidance(adapter)
    section_overview = _render_adapter_entry_sections(_agent_run_sections(adapter=adapter, marker_source=marker_source, context_bits=context_bits))
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


def _codex_loopora_gen_skill() -> str:
    return f"""---
name: loopora-plan
description: "Use when the user invokes /loopora-plan to create, revise, repair, or tighten the reviewed Loop preview without starting a run."
---

<!-- {MANAGED_MARKER} version={CODEX_ADAPTER_VERSION} file=loopora-plan -->

# Loopora Plan

This is a thin dispatcher. Before authoring or repairing a Loop plan, read `references/loopora-plan-contract.md` and follow it as the stable planning contract.

```bash
LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill loopora agent codex plan --workdir "$PWD" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source codex_project_skill
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`; if they say `fresh`, create a new candidate and keep old runs only as history.
"""


def _agent_native_run_entry_contract() -> str:
    bullets = "\n".join(f"- {item}" for item in NATIVE_RUN_ENTRY_CONTRACT_BULLETS)
    return f"## {NATIVE_RUN_ENTRY_CONTRACT_TITLE}\n\n{bullets}\n"


def _codex_loopora_loop_skill() -> str:
    return f"""---
name: loopora-run
description: "Use when the user invokes /loopora-run to start or resume the reviewed Loop preview that preserves the current task judgment and evidence requirements."
---

<!-- {MANAGED_MARKER} version={CODEX_ADAPTER_VERSION} file=loopora-run -->

# Loopora Run

This is a thin dispatcher. Read these managed references before starting role dispatch:

- `references/loopora-run-contract.md`
- `references/loopora-recovery-matrix.md`
- `references/loopora-role-dispatch-guide.md`
- `references/loopora-result-template-guide.md`

{_agent_native_run_entry_contract().rstrip()}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=codex_project_skill loopora agent codex run --workdir "$PWD" --entry-source codex_project_skill --json
```

If the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
"""


def _claude_loopora_gen_skill() -> str:
    return f"""---
name: loopora-plan
description: "Create, revise, repair, or tighten the current Claude Code Loop preview without starting a run. Invoke manually as /loopora-plan."
disable-model-invocation: true
allowed-tools: "Bash(loopora agent claude plan *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *) Bash(LOOPORA_HOME=* loopora agent claude plan *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan *)"
---

<!-- {CLAUDE_MANAGED_MARKER} version={CLAUDE_ADAPTER_VERSION} file=loopora-plan -->

# Loopora Plan

This is a thin dispatcher. Before authoring or repairing a Loop plan, read `references/loopora-plan-contract.md` and follow it as the stable planning contract.

```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude plan --workdir "$PWD" --context-id "${{CLAUDE_SESSION_ID}}" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source claude_project_skill
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`; if they say `fresh`, create a new candidate and keep old runs only as history.
"""


def _claude_loopora_loop_skill() -> str:
    return f"""---
name: loopora-run
description: "Start or reuse the reviewed Loop preview that preserves this Claude Code task judgment and evidence requirements. Invoke manually after /loopora-plan."
disable-model-invocation: true
allowed-tools: "Bash(loopora agent claude run *) Bash(loopora agent claude next *) Bash(loopora agent claude submit *) Bash(loopora agent claude check *) Bash(LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *) Bash(LOOPORA_HOME=* loopora agent claude *) Bash(LOOPORA_HOME=* LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude *) Bash(loopora init claude *) Bash(LOOPORA_HOME=* loopora init claude *) Agent Task"
---

<!-- {CLAUDE_MANAGED_MARKER} version={CLAUDE_ADAPTER_VERSION} file=loopora-run -->

# Loopora Run

This is a thin dispatcher. Read these managed references before starting role dispatch:

- `references/loopora-run-contract.md`
- `references/loopora-recovery-matrix.md`
- `references/loopora-role-dispatch-guide.md`
- `references/loopora-result-template-guide.md`

{_agent_native_run_entry_contract().rstrip()}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=claude_project_skill loopora agent claude run --workdir "$PWD" --context-id "${{CLAUDE_SESSION_ID}}" --entry-source claude_project_skill --json
```

If the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
"""


def _opencode_loopora_gen_command() -> str:
    return f"""---
description: Create, revise, repair, or tighten the current OpenCode Loop preview without starting a run.
---

<!-- {OPENCODE_MANAGED_MARKER} version={OPENCODE_ADAPTER_VERSION} file=loopora-plan -->

# Loopora Plan

This is a thin dispatcher. Before authoring or repairing a Loop plan, read `.opencode/loopora/references/loopora-plan-contract.md` and follow it as the stable planning contract.

## Arguments

`$ARGUMENTS` may contain `fresh` or an existing candidate plan file path. Use the reference contract to decide how to map it.

```bash
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command loopora agent opencode plan --workdir "$PWD" --context-id "${{OPENCODE_SESSION_ID:-}}" --message "<non-empty short task summary>" --bundle-file <candidate-plan-file> --entry-source opencode_project_command
```

`/loopora-plan` never starts a run. If the user wants to continue execution, send them to `/loopora-run`.
"""


def _opencode_loopora_loop_command() -> str:
    return f"""---
description: Start or reuse the reviewed Loop preview that preserves this OpenCode task judgment and evidence requirements.
agent: loopora-orchestrator
subtask: true
---

<!-- {OPENCODE_MANAGED_MARKER} version={OPENCODE_ADAPTER_VERSION} file=loopora-run -->

# Loopora Run

This is a thin dispatcher. Read these managed references before starting role dispatch:

- `.opencode/loopora/references/loopora-run-contract.md`
- `.opencode/loopora/references/loopora-recovery-matrix.md`
- `.opencode/loopora/references/loopora-role-dispatch-guide.md`
- `.opencode/loopora/references/loopora-result-template-guide.md`

{_agent_native_run_entry_contract().rstrip()}

Start or resume with:

```bash
LOOPORA_AGENT_ENTRY_SOURCE=opencode_project_command loopora agent opencode run --workdir "$PWD" --context-id "${{OPENCODE_SESSION_ID:-}}" --entry-source opencode_project_command --json
```

If `$ARGUMENTS` or the user provides `option:<id>`, pass it as `--source-option-id <id>`. If the command returns `loop_recovery`, report the recovery path and stop before dispatching any role agent.
"""
