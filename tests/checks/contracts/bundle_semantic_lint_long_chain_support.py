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
    bundle["collaboration_summary"] = (
        "Compile the search refactor into a long-chain workflow because query rewriting, retrieval, "
        "ranking, regression review, and evidence hardening each create distinct artifacts, handoffs, "
        "and proof targets. Future iterations stay anchored to these phase contracts as new evidence "
        "and blockers appear. GateKeeper must judge from phase evidence rather than only the final "
        f"Builder story, separating {PHASE_EVIDENCE_LABELS} claims."
    )
    bundle["role_definitions"] = [_role_definition(*spec) for spec in ROLE_SPECS]
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
