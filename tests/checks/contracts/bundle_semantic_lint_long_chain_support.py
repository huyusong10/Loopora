from __future__ import annotations

from pathlib import Path

from loopora.bundles import bundle_to_yaml, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


BUNDLE_NAME = "Search Long-Chain Bundle"
PHASE_EVIDENCE_LABELS = "Proven, Weak, Unproven, Blocking, and Residual risk"

BASELINE_INSPECTOR_ROLE_ID = "baseline_inspector"
QUERY_BUILDER_ROLE_ID = "query_builder"
RETRIEVAL_BUILDER_ROLE_ID = "retrieval_builder"
RANKING_BUILDER_ROLE_ID = "ranking_builder"
REGRESSION_INSPECTOR_ROLE_ID = "regression_inspector"
EVIDENCE_HARDENING_BUILDER_ROLE_ID = "evidence_hardening_builder"
GATEKEEPER_ROLE_ID = "gatekeeper"

BASELINE_INSPECTION_STEP_ID = "baseline_inspection_step"
QUERY_BUILDER_STEP_ID = "query_builder_step"
RETRIEVAL_BUILDER_STEP_ID = "retrieval_builder_step"
RANKING_BUILDER_STEP_ID = "ranking_builder_step"
REGRESSION_INSPECTION_STEP_ID = "regression_inspection_step"
EVIDENCE_HARDENING_BUILDER_STEP_ID = "evidence_hardening_builder_step"
GATEKEEPER_STEP_ID = "gatekeeper_step"

ROLE_DEFAULTS = {
    "executor_kind": "codex",
    "executor_mode": "preset",
    "command_cli": "",
    "command_args_text": "",
    "model": "",
    "reasoning_effort": "",
}

ROLE_SPECS = (
    (
        "baseline-inspector",
        "Search Baseline Inspector",
        "inspector",
        "Inspect the current search behavior and pin the first reproducible baseline before implementation.",
        "Treat unsupported baseline claims as Unproven and identify the first proof path the Builders must preserve.",
    ),
    (
        "query-builder",
        "Query Rewrite Builder",
        "builder",
        "Implement only the query rewrite phase and preserve a narrow evidence handoff for retrieval work.",
        "Move query rewrite behavior toward Proven without changing retrieval or ranking standards silently.",
    ),
    (
        "retrieval-builder",
        "Retrieval Builder",
        "builder",
        "Implement only the retrieval phase from the query handoff and leave concrete retrieval evidence.",
        "Preserve the query phase contract while producing a distinct retrieval artifact and proof target.",
    ),
    (
        "ranking-builder",
        "Ranking Builder",
        "builder",
        "Implement only the ranking phase from retrieval evidence and avoid masking recall regressions.",
        "Prefer maintainable ranking progress over metric theater; expose weak proof instead of broad claims.",
    ),
    (
        "regression-inspector",
        "Search Regression Inspector",
        "inspector",
        "Review query, retrieval, and ranking handoffs against the baseline and search regressions.",
        "Mark regressions as Blocking, thin evidence as Weak, and unsupported phase claims as Unproven.",
    ),
    (
        "evidence-hardening-builder",
        "Evidence Hardening Builder",
        "builder",
        "Add only missing proof or harness support requested by regression review.",
        "Do not widen product scope; turn review gaps into durable evidence that GateKeeper can inspect.",
    ),
    (
        "search-gatekeeper",
        "Search Evidence GateKeeper",
        "gatekeeper",
        "Judge the long-chain search refactor from baseline, phase, regression, and evidence-hardening handoffs.",
        "Finish only when critical phase claims are Proven or acceptable Residual risk, and fail closed on Blocking gaps.",
    ),
)


def _role_definition(
    key: str,
    name: str,
    archetype: str,
    body: str,
    posture: str,
) -> dict:
    return {
        "key": key,
        "name": name,
        "description": body,
        "archetype": archetype,
        "prompt_ref": f"{key}.md",
        "prompt_markdown": f"""---
version: 1
archetype: {archetype}
---

{body} Leave a handoff that names {PHASE_EVIDENCE_LABELS} evidence for downstream roles.""",
        "posture_notes": posture,
        **ROLE_DEFAULTS,
    }


def long_chain_multi_builder_bundle(workdir: Path) -> dict:
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))

    bundle["metadata"]["name"] = BUNDLE_NAME
    bundle["loop"]["name"] = BUNDLE_NAME
    local_governance_sentence = (
        " If AGENTS.md, design/README.md, design/, or tests/ are present, route those local governance "
        "markers into Builder reading, Inspector verification, and GateKeeper Weak / Unproven / Blocking "
        "treatment without inventing marker contents."
    )
    bundle["collaboration_summary"] = (
        "Compile the search refactor into a long-chain workflow because query rewriting, retrieval, "
        "ranking, regression review, and evidence hardening each create distinct artifacts, handoffs, "
        "and proof targets. Future iterations stay anchored to these phase contracts as new evidence "
        "and blockers appear. GateKeeper must judge from phase evidence rather than only the final "
        f"Builder story, separating {PHASE_EVIDENCE_LABELS} claims. Each final search claim must be "
        "auditable through baseline artifacts, phase handoffs, command output or logs, and exact evidence IDs."
        f"{local_governance_sentence}"
    )
    bundle["spec"]["markdown"] = f"""# Task

Roll out a search relevance improvement in phases: baseline the current behavior, implement query rewrite, retrieval, and ranking separately, then harden evidence before GateKeeper closure. Keep broad personalization, full search UI redesign, and unrelated tuning out of scope.

# Done When

- Baseline inspection pins the current behavior and the first reproducible proof path.
- Query rewrite, retrieval, and ranking phases each leave distinct handoffs and exact evidence IDs.
- Regression review compares phase evidence to the baseline and names {PHASE_EVIDENCE_LABELS} claims.
- GateKeeper can audit baseline, phase, regression, and evidence-hardening handoffs before finishing.

# Guardrails

- Do not hide recall regressions behind ranking polish.
- Keep each Builder scoped to its phase and preserve upstream phase contracts.
- Treat local governance markers such as AGENTS.md, design/README.md, design/, or tests/ as runtime responsibilities when present.

# Success Surface

- A reviewer can trace each final search claim to baseline artifacts, phase handoffs, command output or logs, and exact evidence IDs.
- GateKeeper can see which claims are Proven, Weak, Unproven, Blocking, or Residual risk before closure.

# Fake Done

- Do not pass a final ranking story with no baseline, phase proof, audit trail, command log, or evidence ID.
- Do not pass when retrieval or recall risk is masked by top-result polish.
- Do not pass unsupported query, retrieval, ranking, or regression claims.
- Do not pass a happy-path-only search demo that leaves recall, retrieval, or phase evidence unverified.

# Evidence Preferences

- Prefer baseline artifacts, project-owned checks, command output or logs, exact evidence IDs, and phase handoffs.
- Regression review should mark weak proof as Weak, unsupported claims as Unproven, closure blockers as Blocking, and accepted tuning leftovers as Residual risk.
- Evidence-hardening work should repair missing proof only; it must not broaden product scope.

# Residual Risk

Minor tuning risk may remain only when labeled as Residual risk and assigned to a follow-up owner or acceptance path. Missing baseline evidence, unproven recall regressions, unsupported phase claims, skipped local governance, or missing audit / log evidence must fail closed.

# Role Notes

## Search Baseline Inspector Notes

Pin current behavior before implementation, identify the first reproducible proof path, and mark unsupported baseline claims as Unproven.

## Query Rewrite Builder Notes

Implement only query rewrite behavior from the baseline handoff, preserve upstream evidence IDs, and leave a narrow handoff for retrieval work.

## Retrieval Builder Notes

Implement only retrieval behavior from the query handoff, preserve query contracts, and leave retrieval evidence that regression review can audit.

## Ranking Builder Notes

Implement only ranking behavior from retrieval evidence, avoid masking recall regressions, and expose Weak or Unproven proof plainly.

## Search Regression Inspector Notes

Compare query, retrieval, and ranking handoffs against the baseline, verify local governance obligations when present, and mark regressions or missing proof as Blocking.

## Evidence Hardening Builder Notes

Add only proof harness, command output, logs, or artifact links requested by regression review; do not widen search behavior.

## Search Evidence GateKeeper Notes

Finish only when baseline, phase, regression, local-governance, and evidence-hardening handoffs prove the task contract; fail closed on Blocking gaps or unmanaged Residual risk.
"""
    role_definitions = []
    for spec in ROLE_SPECS:
        role = _role_definition(*spec)
        if role["archetype"] == "builder":
            role["prompt_markdown"] = role["prompt_markdown"].rstrip() + (
                "\n\nBuilder reads AGENTS.md, design/README.md, design/, and tests/ before editing when present, "
                "then preserves applicable obligations in the phase handoff instead of inventing marker contents.\n"
            )
        elif role["archetype"] == "inspector":
            role["prompt_markdown"] = role["prompt_markdown"].rstrip() + (
                "\n\nInspector verifies AGENTS.md, design/README.md, design/, and tests/ obligations against the result when present, "
                "then classifies skipped obligations as Weak, Unproven, or Blocking.\n"
            )
        elif role["archetype"] == "gatekeeper":
            role["prompt_markdown"] = role["prompt_markdown"].rstrip() + (
                "\n\nGateKeeper treats skipped AGENTS.md, design/README.md, design/, or tests/ evidence as Weak, Unproven, or Blocking. "
                "Treat missing audit/log evidence or uncited evidence IDs as Blocking unless explicitly accepted as managed Residual risk.\n"
            )
        role_definitions.append(role)
    bundle["role_definitions"] = role_definitions
    bundle["workflow"] = {
        "version": 1,
        "preset": "",
        "collaboration_intent": (
            "Use a long-chain phase workflow because the search task has distinct query, retrieval, ranking, "
            "regression, and evidence-hardening proof targets. Each Builder owns one phase handoff; "
            "Regression Inspector checks phase evidence before Evidence Hardening Builder repairs proof gaps; "
            "GateKeeper fans in baseline, regression, and final evidence so weak evidence, drift, or fake done "
            "surface before closure."
        ),
        "roles": [
            {"id": BASELINE_INSPECTOR_ROLE_ID, "role_definition_key": "baseline-inspector"},
            {"id": QUERY_BUILDER_ROLE_ID, "role_definition_key": "query-builder"},
            {"id": RETRIEVAL_BUILDER_ROLE_ID, "role_definition_key": "retrieval-builder"},
            {"id": RANKING_BUILDER_ROLE_ID, "role_definition_key": "ranking-builder"},
            {"id": REGRESSION_INSPECTOR_ROLE_ID, "role_definition_key": "regression-inspector"},
            {"id": EVIDENCE_HARDENING_BUILDER_ROLE_ID, "role_definition_key": "evidence-hardening-builder"},
            {"id": GATEKEEPER_ROLE_ID, "role_definition_key": "search-gatekeeper"},
        ],
        "steps": [
            {"id": BASELINE_INSPECTION_STEP_ID, "role_id": BASELINE_INSPECTOR_ROLE_ID, "on_pass": "continue"},
            {
                "id": QUERY_BUILDER_STEP_ID,
                "role_id": QUERY_BUILDER_ROLE_ID,
                "inputs": {"handoffs_from": [BASELINE_INSPECTION_STEP_ID], "iteration_memory": "summary_only"},
                "on_pass": "continue",
            },
            {
                "id": RETRIEVAL_BUILDER_STEP_ID,
                "role_id": RETRIEVAL_BUILDER_ROLE_ID,
                "inputs": {"handoffs_from": [QUERY_BUILDER_STEP_ID], "iteration_memory": "same_step"},
                "on_pass": "continue",
            },
            {
                "id": RANKING_BUILDER_STEP_ID,
                "role_id": RANKING_BUILDER_ROLE_ID,
                "inputs": {"handoffs_from": [RETRIEVAL_BUILDER_STEP_ID], "iteration_memory": "same_step"},
                "on_pass": "continue",
            },
            {
                "id": REGRESSION_INSPECTION_STEP_ID,
                "role_id": REGRESSION_INSPECTOR_ROLE_ID,
                "inputs": {
                    "handoffs_from": [
                        QUERY_BUILDER_STEP_ID,
                        RETRIEVAL_BUILDER_STEP_ID,
                        RANKING_BUILDER_STEP_ID,
                    ],
                    "evidence_query": {"archetypes": ["builder"], "limit": 30},
                    "iteration_memory": "summary_only",
                },
                "on_pass": "continue",
            },
            {
                "id": EVIDENCE_HARDENING_BUILDER_STEP_ID,
                "role_id": EVIDENCE_HARDENING_BUILDER_ROLE_ID,
                "inputs": {"handoffs_from": [REGRESSION_INSPECTION_STEP_ID], "iteration_memory": "summary_only"},
                "on_pass": "continue",
            },
            {
                "id": GATEKEEPER_STEP_ID,
                "role_id": GATEKEEPER_ROLE_ID,
                "inputs": {
                    "handoffs_from": [
                        BASELINE_INSPECTION_STEP_ID,
                        REGRESSION_INSPECTION_STEP_ID,
                        EVIDENCE_HARDENING_BUILDER_STEP_ID,
                    ],
                    "evidence_query": {"archetypes": ["builder", "inspector"], "limit": 40},
                },
                "on_pass": "finish_run",
            },
        ],
    }
    return load_bundle_text(bundle_to_yaml(bundle))
