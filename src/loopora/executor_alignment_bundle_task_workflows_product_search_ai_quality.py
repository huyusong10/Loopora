from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents


def _replace_search_quality_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    workflow = bundle["workflow"]
    workflow["preset"] = "search-quality-evaluation"
    workflow_intents._replace_search_quality_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "evaluation_baseline_inspector", "role_definition_key": "evaluation-baseline-inspector"},
        {"id": "search_quality_builder", "role_definition_key": "search-quality-builder"},
        {"id": "quality_evidence_inspector", "role_definition_key": "quality-evidence-inspector"},
        {"id": "search_quality_gatekeeper", "role_definition_key": "search-quality-gatekeeper"},
    ]
    quality_verifies = [
        "eval-set",
        "human-review",
        "search-index",
        "monitoring",
        "negative_evidence",
        "local-governance",
    ]
    workflow["steps"] = [
        {"id": "evaluation_baseline_step", "role_id": "evaluation_baseline_inspector", "on_pass": "continue"},
        {
            "id": "search_quality_builder_step",
            "role_id": "search_quality_builder",
            "inputs": {
                "handoffs_from": ["evaluation_baseline_step"],
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "quality_evidence_step",
            "role_id": "quality_evidence_inspector",
            "inputs": {
                "handoffs_from": ["evaluation_baseline_step", "search_quality_builder_step"],
                "evidence_query": {
                    "archetypes": ["builder", "inspector"],
                    "verifies": quality_verifies,
                    "limit": 36,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "search_quality_gatekeeper_step",
            "role_id": "search_quality_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "evaluation_baseline_step",
                    "search_quality_builder_step",
                    "quality_evidence_step",
                ],
                "evidence_query": {
                    "archetypes": ["builder", "inspector"],
                    "verifies": quality_verifies,
                    "limit": 44,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
