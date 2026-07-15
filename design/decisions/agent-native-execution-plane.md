# Agent-Native Execution Plane

## Status

Accepted.

## Context

Loopora originally grew around a headless runner: Core registered a run, then a local worker called provider executors for each role step. That path is still useful for CI, automation, custom commands and legacy runs.

The current first-use model routes by context: Fit Guide/Web choices are the outside-Agent route,
letting a reviewed task continue into Web conversation, Plan File import, or manual expert creation;
Agent Native is the same-Agent path when the user is already inside Codex, Claude Code or OpenCode.
In that Agent path, the host Agent should remain the execution subject. If `/loopora-run` starts
provider CLI subprocesses behind that host, Loopora becomes a nested Agent runner and loses the
product boundary described by Human-Shaped Loop: Loopora should hold the Loop state, evidence and
verdict while the current Agent advances the task under that governance structure.

## Decision

Loopora keeps two explicit execution planes:

| Plane | Execution subject | Stable entry |
| --- | --- | --- |
| `agent_native` | Current Coding Agent and its native subagent / task mechanism | `/loopora-plan`, `/loopora-run`, `loopora agent <adapter> next/submit` |
| `headless` | Loopora worker invoking executor subprocesses | Web-owned runs, `loopora loops run`, background worker, CI and custom automation |

Same-Agent `/loopora-run` must create or reuse an `agent_native` run. It may register the run and return an Agent Step View projection, but it must not spawn Codex, Claude Code or OpenCode CLI subprocesses to simulate role work.

Same-Agent `/loopora-plan` follows the same execution-subject rule. Fit clarification, Loop-shaping questions, working-agreement review, explicit confirmation, and candidate authoring stay in the current host main session. Only after confirmation does the host submit a candidate file to Loopora Core for validation. The message-only CLI path is an explicit non-interactive/Web fallback; because that fallback may use the separate alignment executor plane, managed entries must not invoke it as the first same-Agent planning action.

The Agent Step View is the handoff projection between Loopora Core and the host Agent. It must carry the full step prompt, target native role agent, frozen `judgment_contract`, required coverage summary, context refs, evidence rules and output schema. The host may choose the native subagent / task mechanism, but it must not reconstruct these fields from memory or from a shortened prompt.

Host-native todo/progress lists and user-question affordances are adapter experience projections, not proof. They should mirror Loopora's current handoff when available, while Core still treats evidence refs, handoffs, coverage and task verdicts as the fact source. Host-native subagent/task trace ids are optional dispatch proof enrichments: preserve them when exposed by the host, but do not invent them or block older hosts solely because no trace id is available.

The headless path remains a first-class automation path and the execution plane for Web-owned runs. It uses the executor subsystem, structured output contracts, timeout handling and legacy compatibility rules. It is not the implementation of the same-Agent entry.

## Consequences

- Bundle `executor_kind` / `executor_mode` stay in assets for compatibility, Web alignment defaults and headless fallback, but they do not cause nested provider CLI execution in an Agent-native run.
- Host-native planning avoids hidden background alignment work and duplicate provider cost before candidate validation; Web alignment remains available when the host cannot continue the dialogue or the user chooses it.
- Agent Native plan/run/submit may discover and reuse a responding same-App-home Web instance, but never spawn a detached Web service. Explicit foreground `loopora serve` owns startup and Ctrl-C shutdown.
- `agent_native` runs can be `awaiting_agent`; this is an active run lifecycle state, not a terminal result and not a hidden background worker.
- Host submissions must carry dispatch proof, and Core remains the evidence, handoff, coverage and GateKeeper verdict fact source.
- Agent-native execution preserves the same human judgment contract as headless execution: bundle judgment freezes into the run contract, then projects into every Agent Step View and terminal observation surface.
- Web can compose Loops for headless execution and observe both execution planes, but user-facing status must distinguish an Agent-native run waiting for host work from a headless worker actively running.

## Validation

- Agent Native behavior checks cover READY binding, `agent_native` state, dispatch proof, frozen judgment, required coverage, result templates, and host-owned execution.
- `tests/checks/contracts/test_agent_native_role_dispatch_message.py`, `tests/checks/contracts/test_agent_native_result_template_contract.py`, and `tests/checks/contracts/test_web_error_boundaries.py` cover the current role-dispatch, Agent Step View result, and foreground-Web boundaries.
- `tests/probes/real_environment/run_real_probes.py --suite real-agent` is the release-profile real-host check for managed Agent entries.
- `tests/probes/real_environment/run_real_probes.py --suite real-cli` keeps the explicit headless/provider CLI boundary covered separately.
