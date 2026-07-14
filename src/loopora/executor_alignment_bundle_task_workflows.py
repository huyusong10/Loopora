from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents
from loopora.executor_alignment_bundle_task_workflow_helpers import _dedupe_values
from loopora.executor_alignment_task_projection import alignment_task_domain_projection


def _replace_generic_task_evidence_repair_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    task: str,
    display_language: str = "",
) -> None:
    projection = alignment_task_domain_projection(task, display_language="zh" if prefers_chinese else display_language)
    inspector_verifies = projection.evidence_verifies
    gatekeeper_verifies = _dedupe_values(["done_when", "fake_done", "evidence_buckets", "residual_risk", *projection.evidence_verifies])
    workflow = bundle["workflow"]
    workflow["preset"] = "task-evidence-repair"
    workflow_intents._replace_generic_task_evidence_repair_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "task_builder", "role_definition_key": "task-builder"},
        {"id": "task_inspector", "role_definition_key": "task-inspector"},
        {"id": "task_repair_guide", "role_definition_key": "task-repair-guide"},
        {"id": "task_repair_builder", "role_definition_key": "task-repair-builder"},
        {"id": "task_gatekeeper", "role_definition_key": "task-gatekeeper"},
    ]
    workflow["steps"] = [
        {"id": "build_task_loop", "role_id": "task_builder", "on_pass": "continue"},
        {
            "id": "inspect_task_evidence",
            "role_id": "task_inspector",
            "inputs": {
                "handoffs_from": ["build_task_loop"],
                "evidence_query": {
                    "archetypes": ["builder"],
                    "verifies": inspector_verifies,
                    "limit": 16,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "guide_task_repair",
            "role_id": "task_repair_guide",
            "inputs": {
                "handoffs_from": ["inspect_task_evidence"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": ["weak_unproven_blocking_findings", "repair_direction"],
                    "limit": 16,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "repair_task_evidence",
            "role_id": "task_repair_builder",
            "inputs": {
                "handoffs_from": ["guide_task_repair", "inspect_task_evidence"],
                "evidence_query": {
                    "archetypes": ["inspector", "guide"],
                    "verifies": ["repair_direction", "task_anchor"],
                    "limit": 18,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "gatekeep_task_verdict",
            "role_id": "task_gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "build_task_loop",
                    "inspect_task_evidence",
                    "guide_task_repair",
                    "repair_task_evidence",
                ],
                "evidence_query": {
                    "archetypes": ["builder", "inspector", "guide"],
                    "verifies": gatekeeper_verifies,
                    "limit": 28,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
