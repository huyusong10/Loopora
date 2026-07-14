from __future__ import annotations

from loopora import executor_alignment_bundle_task_workflow_intents as workflow_intents


def _replace_rag_long_chain_task_workflow(
    bundle: dict,
    *,
    prefers_chinese: bool,
    display_language: str = "",
) -> None:
    workflow = bundle["workflow"]
    workflow["preset"] = "rag-grounding-long-chain"
    workflow_intents._replace_rag_long_chain_task_workflow_intent(
        bundle,
        prefers_chinese=prefers_chinese,
        display_language=display_language,
    )
    workflow["roles"] = [
        {"id": "contract_inspector", "role_definition_key": "rag-contract-inspector"},
        {"id": "ingestion_builder", "role_definition_key": "corpus-ingestion-builder"},
        {"id": "retrieval_builder", "role_definition_key": "retrieval-acl-builder"},
        {"id": "answer_builder", "role_definition_key": "answer-tooling-builder"},
        {"id": "evaluation_inspector", "role_definition_key": "rag-evaluation-inspector"},
        {"id": "evidence_builder", "role_definition_key": "evidence-hardening-builder"},
        {"id": "gatekeeper", "role_definition_key": "rag-gatekeeper"},
    ]
    evaluation_verifies = [
        "rag-grounding",
        "tool-safety",
        "permission-auth",
        "privacy-redaction",
        "eval-set",
        "human-review",
        "monitoring",
        "local-governance",
    ]
    workflow["steps"] = [
        {"id": "contract_inspection_step", "role_id": "contract_inspector", "on_pass": "continue"},
        {
            "id": "ingestion_builder_step",
            "role_id": "ingestion_builder",
            "inputs": {"handoffs_from": ["contract_inspection_step"], "iteration_memory": "summary_only"},
            "on_pass": "continue",
        },
        {
            "id": "retrieval_builder_step",
            "role_id": "retrieval_builder",
            "inputs": {"handoffs_from": ["ingestion_builder_step"], "iteration_memory": "same_step"},
            "on_pass": "continue",
        },
        {
            "id": "answer_builder_step",
            "role_id": "answer_builder",
            "inputs": {"handoffs_from": ["retrieval_builder_step"], "iteration_memory": "same_step"},
            "on_pass": "continue",
        },
        {
            "id": "evaluation_inspection_step",
            "role_id": "evaluation_inspector",
            "inputs": {
                "handoffs_from": ["ingestion_builder_step", "retrieval_builder_step", "answer_builder_step"],
                "evidence_query": {"archetypes": ["builder"], "verifies": evaluation_verifies, "limit": 40},
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "evidence_hardening_builder_step",
            "role_id": "evidence_builder",
            "inputs": {
                "handoffs_from": ["evaluation_inspection_step"],
                "evidence_query": {
                    "archetypes": ["inspector"],
                    "verifies": ["weak_unproven_blocking_findings", "rag-grounding", "tool-safety", "eval-set"],
                    "limit": 24,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "continue",
        },
        {
            "id": "gatekeeper_step",
            "role_id": "gatekeeper",
            "inputs": {
                "handoffs_from": [
                    "contract_inspection_step",
                    "evaluation_inspection_step",
                    "evidence_hardening_builder_step",
                ],
                "evidence_query": {
                    "archetypes": ["builder", "inspector"],
                    "verifies": evaluation_verifies,
                    "limit": 50,
                },
                "iteration_memory": "summary_only",
            },
            "on_pass": "finish_run",
        },
    ]
