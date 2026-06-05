from __future__ import annotations


PROOF_COMMAND_OUTPUT_PROMPT_GUIDANCE = (
    "Proof command output rule: Do not pipe proof, sanity, discovery, directory-listing, context-check, or "
    "evidence-producing commands through `head`, `head -c`, `tail`, `sed`, `jq`, `grep`, `wc`, Python string "
    "slicing, or other truncating/filtering wrappers. Do not run a truncated or filtered fallback. Preserve "
    "complete output plus an explicit exit code in the transcript or a cited artifact before summarizing. If you "
    "need directory or file discovery as context, use host Read/Glob/Grep when available or preserve the complete "
    "listing; do not replace it with `ls ... | head`, snippet probes, or count-only probes. If you save proof "
    "output to an artifact, write it directly to a task-owned path or "
    "`.loopora/agent_artifacts/<run_id>/<step_id>/`; do not stage it in `/tmp` and copy it later. Capture command "
    "output and `EXIT_CODE=<code>` in one shell command; do not first run an incomplete redirect and rerun the same "
    "proof only to add the exit code. "
    "Do not validate proof artifacts with `wc`, line counts, byte counts, or other count-only probes instead of "
    "reading the preserved output you cite. "
    "Proof logs are task artifacts, not Loopora submit wrappers: do not write them under `.loopora/agent_outbox` "
    "or to any `*.result.json` path. Use a task-owned path or `.loopora/agent_artifacts/<run_id>/<step_id>/`."
)

INSPECTOR_PRIMARY_PROOF_PROMPT_GUIDANCE = (
    "Inspector primary proof rule: Treat explicit Done When/check commands, evidence-preference commands, and "
    "fresh upstream task-owned proof artifacts as primary proof. Inspect known upstream evidence refs and cited "
    "artifacts first. If a fresh complete successful upstream artifact already covers a listed check id or coverage "
    "target, map it into check_results, coverage_results, or tester_observations without rerunning the identical "
    "command. When the upstream proof is missing, stale, ambiguous, conflicting, invalid, or no sufficient upstream "
    "artifact exists, and one exact command covers a listed check id or coverage target, run that exact command with "
    "complete output and an explicit exit code, then map its result into check_results, coverage_results, or "
    "tester_observations. Do not add broader discovery/sanity variants unless the primary command fails, is ambiguous, "
    "or leaves a specific uncovered target that the extra command is designed to resolve."
)
