from __future__ import annotations


ARTIFACT_REF_SCHEMA = {
    "type": "object",
    "required": ["kind", "label", "relative_path", "workspace_path", "absolute_path"],
    "properties": {
        "kind": {"type": "string"},
        "label": {"type": "string"},
        "relative_path": {"type": "string"},
        "workspace_path": {"type": "string"},
        "absolute_path": {"type": "string"},
    },
    "additionalProperties": False,
}

EVIDENCE_COVERAGE_RESULT_SCHEMA = {
    "type": "object",
    "required": ["target_id", "status", "evidence_refs", "note"],
    "properties": {
        "target_id": {"type": "string"},
        "status": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
        "note": {"type": "string"},
    },
    "additionalProperties": False,
}

EVIDENCE_COVERAGE_GAP_SCHEMA = {
    "type": "object",
    "required": ["target_id", "kind", "source_section", "status", "required", "reason", "text", "evidence_refs"],
    "properties": {
        "target_id": {"type": "string"},
        "kind": {"type": "string"},
        "source_section": {"type": "string"},
        "status": {"type": "string"},
        "required": {"type": "boolean"},
        "reason": {"type": "string"},
        "text": {"type": "string"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}

EVIDENCE_ITEM_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "timestamp",
        "iter",
        "step_id",
        "step_order",
        "role_id",
        "role_name",
        "runtime_role",
        "archetype",
        "evidence_kind",
        "source",
        "method",
        "claim",
        "result",
        "verifies",
        "related_evidence_ids",
        "coverage_results",
        "measured_evidence",
        "concrete_evidence_claim_count",
        "residual_risk",
        "artifact_refs",
    ],
    "properties": {
        "id": {"type": "string"},
        "timestamp": {"type": "string"},
        "iter": {"type": "integer"},
        "step_id": {"type": "string"},
        "step_order": {"type": "integer"},
        "role_id": {"type": "string"},
        "role_name": {"type": "string"},
        "runtime_role": {"type": "string"},
        "archetype": {"type": "string"},
        "evidence_kind": {"type": "string"},
        "source": {"type": "string"},
        "method": {"type": "string"},
        "claim": {"type": "string"},
        "result": {"type": "string"},
        "verifies": {"type": "array", "items": {"type": "string"}},
        "related_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "coverage_results": {"type": "array", "items": EVIDENCE_COVERAGE_RESULT_SCHEMA},
        "measured_evidence": {"type": "boolean"},
        "concrete_evidence_claim_count": {"type": "integer"},
        "residual_risk": {"type": "string"},
        "artifact_refs": {"type": "array", "items": ARTIFACT_REF_SCHEMA},
    },
    "additionalProperties": False,
}

EVIDENCE_MANIFEST_SUMMARY_SCHEMA = {
    "type": "object",
    "required": [
        "claim_count",
        "direct_proof_claim_count",
        "workspace_artifact_claim_count",
        "run_artifact_claim_count",
        "ledger_only_claim_count",
        "unverified_claim_count",
        "problem_count",
    ],
    "properties": {
        "claim_count": {"type": "integer"},
        "direct_proof_claim_count": {"type": "integer"},
        "workspace_artifact_claim_count": {"type": "integer"},
        "run_artifact_claim_count": {"type": "integer"},
        "ledger_only_claim_count": {"type": "integer"},
        "unverified_claim_count": {"type": "integer"},
        "problem_count": {"type": "integer"},
    },
    "additionalProperties": False,
}

EVIDENCE_MANIFEST_CLAIM_TARGET_SCHEMA = {
    "type": "object",
    "required": ["id", "kind", "label", "reported_status", "coverage_status", "required", "evidence_refs"],
    "properties": {
        "id": {"type": "string"},
        "kind": {"type": "string"},
        "label": {"type": "string"},
        "reported_status": {"type": "string"},
        "coverage_status": {"type": "string"},
        "required": {"type": "boolean"},
        "evidence_refs": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}

EVIDENCE_MANIFEST_CLAIM_SCHEMA = {
    "type": "object",
    "required": [
        "id",
        "verification_status",
        "measured_evidence",
        "concrete_evidence_claim_count",
        "artifact_count",
        "artifact_backed",
        "workspace_backed",
        "reproducible",
        "coverage_targets",
        "problem_codes",
    ],
    "properties": {
        "id": {"type": "string"},
        "verification_status": {"type": "string"},
        "measured_evidence": {"type": "boolean"},
        "concrete_evidence_claim_count": {"type": "integer"},
        "artifact_count": {"type": "integer"},
        "artifact_backed": {"type": "boolean"},
        "workspace_backed": {"type": "boolean"},
        "reproducible": {"type": "boolean"},
        "coverage_targets": {"type": "array", "items": EVIDENCE_MANIFEST_CLAIM_TARGET_SCHEMA},
        "problem_codes": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}
