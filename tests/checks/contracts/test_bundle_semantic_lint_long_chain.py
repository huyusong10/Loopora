from __future__ import annotations

from pathlib import Path

from loopora.bundles import bundle_to_yaml, lint_alignment_bundle_semantics, load_bundle_text
from loopora.executor_fake_payloads import alignment_bundle_yaml


def _long_chain_multi_builder_bundle(workdir: Path) -> dict:
    bundle = load_bundle_text(alignment_bundle_yaml(str(workdir.resolve())))
    role_defaults = {
        "executor_kind": "codex",
        "executor_mode": "preset",
        "command_cli": "",
        "command_args_text": "",
        "model": "",
        "reasoning_effort": "",
    }

    def role(
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

{body} Leave a handoff that names Proven, Weak, Unproven, Blocking, and Residual risk evidence for downstream roles.""",
            "posture_notes": posture,
            **role_defaults,
        }

    bundle["metadata"]["name"] = "Search Long-Chain Bundle"
    bundle["loop"]["name"] = "Search Long-Chain Bundle"
    bundle["collaboration_summary"] = (
        "Compile the search refactor into a long-chain workflow because query rewriting, retrieval, "
        "ranking, regression review, and evidence hardening each create distinct artifacts, handoffs, "
        "and proof targets. Future iterations stay anchored to these phase contracts as new evidence "
        "and blockers appear. GateKeeper must judge from phase evidence rather than only the final "
        "Builder story, separating Proven, Weak, Unproven, Blocking, and Residual risk claims."
    )
    bundle["role_definitions"] = [
        role(
            "baseline-inspector",
            "Search Baseline Inspector",
            "inspector",
            "Inspect the current search behavior and pin the first reproducible baseline before implementation.",
            "Treat unsupported baseline claims as Unproven and identify the first proof path the Builders must preserve.",
        ),
        role(
            "query-builder",
            "Query Rewrite Builder",
            "builder",
            "Implement only the query rewrite phase and preserve a narrow evidence handoff for retrieval work.",
            "Move query rewrite behavior toward Proven without changing retrieval or ranking standards silently.",
        ),
        role(
            "retrieval-builder",
            "Retrieval Builder",
            "builder",
            "Implement only the retrieval phase from the query handoff and leave concrete retrieval evidence.",
            "Preserve the query phase contract while producing a distinct retrieval artifact and proof target.",
        ),
        role(
            "ranking-builder",
            "Ranking Builder",
            "builder",
            "Implement only the ranking phase from retrieval evidence and avoid masking recall regressions.",
            "Prefer maintainable ranking progress over metric theater; expose weak proof instead of broad claims.",
        ),
        role(
            "regression-inspector",
            "Search Regression Inspector",
            "inspector",
            "Review query, retrieval, and ranking handoffs against the baseline and search regressions.",
            "Mark regressions as Blocking, thin evidence as Weak, and unsupported phase claims as Unproven.",
        ),
        role(
            "evidence-hardening-builder",
            "Evidence Hardening Builder",
            "builder",
            "Add only missing proof or harness support requested by regression review.",
            "Do not widen product scope; turn review gaps into durable evidence that GateKeeper can inspect.",
        ),
        role(
            "search-gatekeeper",
            "Search Evidence GateKeeper",
            "gatekeeper",
            "Judge the long-chain search refactor from baseline, phase, regression, and evidence-hardening handoffs.",
            "Finish only when critical phase claims are Proven or acceptable Residual risk, and fail closed on Blocking gaps.",
        ),
    ]
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
            {"id": "baseline_inspector", "role_definition_key": "baseline-inspector"},
            {"id": "query_builder", "role_definition_key": "query-builder"},
            {"id": "retrieval_builder", "role_definition_key": "retrieval-builder"},
            {"id": "ranking_builder", "role_definition_key": "ranking-builder"},
            {"id": "regression_inspector", "role_definition_key": "regression-inspector"},
            {"id": "evidence_hardening_builder", "role_definition_key": "evidence-hardening-builder"},
            {"id": "gatekeeper", "role_definition_key": "search-gatekeeper"},
        ],
        "steps": [
            {"id": "baseline_inspection_step", "role_id": "baseline_inspector", "on_pass": "continue"},
            {
                "id": "query_builder_step",
                "role_id": "query_builder",
                "inputs": {"handoffs_from": ["baseline_inspection_step"], "iteration_memory": "summary_only"},
                "on_pass": "continue",
            },
            {
                "id": "retrieval_builder_step",
                "role_id": "retrieval_builder",
                "inputs": {"handoffs_from": ["query_builder_step"], "iteration_memory": "same_step"},
                "on_pass": "continue",
            },
            {
                "id": "ranking_builder_step",
                "role_id": "ranking_builder",
                "inputs": {"handoffs_from": ["retrieval_builder_step"], "iteration_memory": "same_step"},
                "on_pass": "continue",
            },
            {
                "id": "regression_inspection_step",
                "role_id": "regression_inspector",
                "inputs": {
                    "handoffs_from": [
                        "query_builder_step",
                        "retrieval_builder_step",
                        "ranking_builder_step",
                    ],
                    "evidence_query": {"archetypes": ["builder"], "limit": 30},
                    "iteration_memory": "summary_only",
                },
                "on_pass": "continue",
            },
            {
                "id": "evidence_hardening_builder_step",
                "role_id": "evidence_hardening_builder",
                "inputs": {"handoffs_from": ["regression_inspection_step"], "iteration_memory": "summary_only"},
                "on_pass": "continue",
            },
            {
                "id": "gatekeeper_step",
                "role_id": "gatekeeper",
                "inputs": {
                    "handoffs_from": [
                        "baseline_inspection_step",
                        "regression_inspection_step",
                        "evidence_hardening_builder_step",
                    ],
                    "evidence_query": {"archetypes": ["builder", "inspector"], "limit": 40},
                },
                "on_pass": "finish_run",
            },
        ],
    }
    return load_bundle_text(bundle_to_yaml(bundle))


def test_alignment_semantic_lint_accepts_long_chain_multi_builder_workflows(
    sample_workdir: Path,
) -> None:
    bundle = _long_chain_multi_builder_bundle(sample_workdir)

    issues = lint_alignment_bundle_semantics(bundle)

    assert issues == []


def test_alignment_semantic_lint_requires_long_chain_gatekeeper_to_read_phase_handoffs(
    sample_workdir: Path,
) -> None:
    bundle = _long_chain_multi_builder_bundle(sample_workdir)
    steps_by_id = {step["id"]: step for step in bundle["workflow"]["steps"]}
    steps_by_id["gatekeeper_step"]["inputs"]["handoffs_from"] = ["evidence_hardening_builder_step"]

    issues = lint_alignment_bundle_semantics(bundle)

    assert ("long-chain GateKeeper must include an earlier phase, review, or Guide handoff in inputs.handoffs_from: gatekeeper_step") in issues
