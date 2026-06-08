## Native Run Contract

- Read the top-level JSON `summary` before `raw.legacy` diagnostics; this is the v3 Agent envelope summary.
- Start only from `/loopora-plan`, `/loopora-run`, or explicit Loopora CLI commands; host hooks or session start must not auto-trigger Loopora work.
- Dispatch only through the host-native role agent named by `next_step.role_dispatch.target_agent`; if unavailable, stop before submit.
- Treat host auto-activation, compatibility routing, or rule injection as context hints, not Loopora dispatch proof.
- Use the context, step-contract, and result-template paths for role handoff; do not replace them with a large inline prompt.
- Do not copy credentials, API keys, tokens, or environment secrets into result files; use redacted evidence references.
- Do not fan out to multiple role agents unless the reviewed Loop workflow exposes a parallel group.
- Treat `complete` as run lifecycle only; task proof comes from `task_proven`, `task_outcome`, and `run.task_verdict`.
- Use the exact Loopora context card or surfaced recoverable choices; do not auto-discover or take over host historical sessions.
- Never start codex, claude, or opencode as nested provider CLIs.
