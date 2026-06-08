---
id: agent-native-behavior
title: Agent Native Behavior Review
targets:
  - id: real-probe-phase-reports
    type: artifact_paths
    title: Agent-native phase reports and explicit behavior artifacts
    optional: true
    globs:
      - .loopora/real-probes/*phase-report.json
      - .loopora/real-probes/**/*phase-report.json
    paths_env: LOOPORA_REVIEW_ARTIFACTS
  - id: agent-native-handbook
    type: text_globs
    title: Agent-native design and probe handbook
    globs:
      - design/contracts.md
      - design/decisions/agent-native-execution-plane.md
      - src/loopora/assets/system_prompts/agent_native/*.md
      - src/loopora/agent_adapter_role_contracts.py
      - tests/probes/real_environment/README.md
      - tests/probes/real_environment/test_real_agent_adapter_probe.py
      - tests/probes/real_environment/run_real_probes.py
    max_bytes_per_file: 64000
  - id: agent-native-risk-hints
    type: term_hints
    title: Agent-native shortcut-risk hints
    optional: true
    globs:
      - .loopora/real-probes/*phase-report.json
      - .loopora/real-probes/**/*phase-report.json
    terms:
      - inline
      - nested
      - prewritten
      - host dispatch
---

Review a real or recorded Agent-host run for whether the host behaves like a Loopora-managed Agent path rather than an inline shortcut.

Look for:

- The host creating the candidate bundle from the conversation brief instead of relying on a prewritten candidate.
- `/loopora-plan` preceding `/loopora-run` through the managed entry surface, with provenance visible in binding evidence.
- First-screen summaries exposing an `agent_work_panel` that tells the host Agent the current state, next action, evidence focus, gaps, user question, todo items, and run URL before technical handoff paths.
- Role work being claimed and submitted through the host-native role/subagent mechanism; the host should use the host's native role/subagent mechanism named by `role_dispatch.target_agent` instead of silently completing work inline.
- Native todo/progress updates mirroring the Loopora handoff when the host supports them, without treating todo state as task evidence.
- Missing Loop-shaping information being routed to the main Agent session as one clear user question with reply shape and decision impact, not asked by a role subagent.
- Optional native subagent/task trace ids being preserved when the host exposes them, without inventing trace proof when unavailable.
- `diagnostics.experience_health` showing whether the work panel was host-visible, whether Loopora artifacts exposed the panel, and whether todo guidance, not-evidence marker, user-question guidance, role-dispatch guidance, native trace, and auto-repair events were observed in the recorded phase report.
- Builder evidence being concrete enough for GateKeeper to cite, and GateKeeper citing known evidence rather than a self-report.
- The host avoiding nested calls to its own CLI from inside the Loopora run.
- Failure triage evidence being understandable without watching stdout live.

This case absorbs the old Agent-first adapter scenario. The real probe handbook and deterministic checks hold the hard invariants; this review checks the recorded run still feels like a managed Agent-native Loop rather than a shortcut wrapped in adapter language.

Hard invariants that are stable and machine-checkable belong in real probes. This case is for the surrounding judgment: whether the run still reads like the intended Agent-native product experience.
