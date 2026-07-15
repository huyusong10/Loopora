from __future__ import annotations

from loopora.context_schema_evidence import (
    ARTIFACT_REF_SCHEMA as ARTIFACT_REF_SCHEMA,
    EVIDENCE_COVERAGE_GAP_SCHEMA as EVIDENCE_COVERAGE_GAP_SCHEMA,
    EVIDENCE_COVERAGE_RESULT_SCHEMA as EVIDENCE_COVERAGE_RESULT_SCHEMA,
    EVIDENCE_ITEM_SCHEMA as EVIDENCE_ITEM_SCHEMA,
    EVIDENCE_MANIFEST_CLAIM_SCHEMA as EVIDENCE_MANIFEST_CLAIM_SCHEMA,
    EVIDENCE_MANIFEST_CLAIM_TARGET_SCHEMA as EVIDENCE_MANIFEST_CLAIM_TARGET_SCHEMA,
    EVIDENCE_MANIFEST_SUMMARY_SCHEMA as EVIDENCE_MANIFEST_SUMMARY_SCHEMA,
)

STEP_HANDOFF_SCHEMA = {
    "type": "object",
    "required": [
        "source",
        "status",
        "summary",
        "blocking_items",
        "recommended_next_action",
        "evidence_refs",
        "artifact_refs",
    ],
    "properties": {
        "source": {
            "type": "object",
            "required": ["iter", "step_id", "step_order", "role_id", "role_name", "runtime_role", "archetype"],
            "properties": {
                "iter": {"type": "integer"},
                "step_id": {"type": "string"},
                "step_order": {"type": "integer"},
                "role_id": {"type": "string"},
                "role_name": {"type": "string"},
                "runtime_role": {"type": "string"},
                "archetype": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "status": {"type": "string"},
        "summary": {"type": "string"},
        "blocking_items": {"type": "array", "items": {"type": "string"}},
        "recommended_next_action": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "artifact_refs": {"type": "array", "items": ARTIFACT_REF_SCHEMA},
    },
    "additionalProperties": False,
}

ROLE_POSTURE_CONTRACT_SCHEMA = {
    "type": "object",
    "required": ["role_id", "role_name", "archetype", "posture_notes"],
    "properties": {
        "role_id": {"type": "string"},
        "role_name": {"type": "string"},
        "archetype": {"type": "string"},
        "posture_notes": {"type": "string"},
    },
    "additionalProperties": False,
}

TASK_VERDICT_BUCKETS_SCHEMA = {
    "type": "object",
    "required": ["proven", "weak", "unproven", "blocking", "residual_risk"],
    "properties": {
        "proven": {"type": "array", "items": {"type": "object"}},
        "weak": {"type": "array", "items": {"type": "object"}},
        "unproven": {"type": "array", "items": {"type": "object"}},
        "blocking": {"type": "array", "items": {"type": "object"}},
        "residual_risk": {"type": "array", "items": {"type": "object"}},
    },
    "additionalProperties": False,
}

TASK_VERDICT_CONTEXT_SCHEMA = {
    "type": "object",
    "required": ["status", "source", "summary", "buckets"],
    "properties": {
        "status": {"type": "string"},
        "source": {"type": "string"},
        "summary": {"type": "string"},
        "buckets": TASK_VERDICT_BUCKETS_SCHEMA,
    },
    "additionalProperties": False,
}

CONTINUATION_COVERAGE_SCHEMA = {
    "type": "object",
    "required": [
        "status",
        "covered_check_count",
        "missing_check_count",
        "target_count",
        "covered_target_count",
        "weak_target_count",
        "missing_target_count",
        "blocked_target_count",
        "covered_check_ids",
        "missing_check_ids",
        "top_gaps",
    ],
    "properties": {
        "status": {"type": "string"},
        "covered_check_count": {"type": "integer"},
        "missing_check_count": {"type": "integer"},
        "target_count": {"type": "integer"},
        "covered_target_count": {"type": "integer"},
        "weak_target_count": {"type": "integer"},
        "missing_target_count": {"type": "integer"},
        "blocked_target_count": {"type": "integer"},
        "covered_check_ids": {"type": "array", "items": {"type": "string"}},
        "missing_check_ids": {"type": "array", "items": {"type": "string"}},
        "top_gaps": {"type": "array", "items": EVIDENCE_COVERAGE_GAP_SCHEMA},
    },
    "additionalProperties": False,
}

CONTINUATION_CONTEXT_SCHEMA = {
    "type": "object",
    "required": [
        "active",
        "reason",
        "previous_run_id",
        "previous_run_path",
        "previous_run_status",
        "previous_task_verdict",
        "previous_task_verdict_path",
        "previous_evidence_coverage_path",
        "coverage",
        "next_focus",
    ],
    "properties": {
        "active": {"type": "boolean"},
        "reason": {"type": "string"},
        "previous_run_id": {"type": "string"},
        "previous_run_path": {"type": "string"},
        "previous_run_status": {"type": "string"},
        "previous_task_verdict": TASK_VERDICT_CONTEXT_SCHEMA,
        "previous_task_verdict_path": {"type": "string"},
        "previous_evidence_coverage_path": {"type": "string"},
        "coverage": CONTINUATION_COVERAGE_SCHEMA,
        "next_focus": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
