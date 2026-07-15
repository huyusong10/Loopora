from __future__ import annotations

"""Normalization helpers for StepInstruction context payloads."""

from loopora.context_contract_snapshot import (
    contract_mapping_list as _contract_mapping_list,
    contract_string as _contract_string,
    contract_string_list as _contract_string_list,
)
from loopora.context_value_helpers import evidence_coverage_results as _evidence_coverage_results
from loopora.context_value_helpers import normalize_coverage_gap_rows as _normalize_coverage_gap_rows
from loopora.context_value_helpers import normalize_manifest_claim_coverage_targets as normalize_manifest_claim_coverage_targets
from loopora.context_value_helpers import string_list as _string_list
from loopora.utils import structured_bool_is_true
from loopora.utils import structured_non_negative_int


def int_value(value: object) -> int:
    return structured_non_negative_int(value)


def empty_task_verdict_context() -> dict:
    return {
        "status": "",
        "source": "",
        "summary": "",
        "buckets": {
            "proven": [],
            "weak": [],
            "unproven": [],
            "blocking": [],
            "residual_risk": [],
        },
    }


def normalize_task_verdict_context(value: object) -> dict:
    if not isinstance(value, dict):
        return empty_task_verdict_context()
    buckets = value.get("buckets") if isinstance(value.get("buckets"), dict) else {}
    return {
        "status": _contract_string(value.get("status")),
        "source": _contract_string(value.get("source")),
        "summary": _contract_string(value.get("summary")),
        "buckets": {
            "proven": _contract_mapping_list(buckets.get("proven")),
            "weak": _contract_mapping_list(buckets.get("weak")),
            "unproven": _contract_mapping_list(buckets.get("unproven")),
            "blocking": _contract_mapping_list(buckets.get("blocking")),
            "residual_risk": _contract_mapping_list(buckets.get("residual_risk")),
        },
    }


def empty_continuation_context() -> dict:
    return {
        "active": False,
        "reason": "",
        "previous_run_id": "",
        "previous_run_path": "",
        "previous_run_status": "",
        "previous_task_verdict": empty_task_verdict_context(),
        "previous_task_verdict_path": "",
        "previous_evidence_coverage_path": "",
        "coverage": {
            "status": "pending",
            "covered_check_count": 0,
            "missing_check_count": 0,
            "target_count": 0,
            "covered_target_count": 0,
            "weak_target_count": 0,
            "missing_target_count": 0,
            "blocked_target_count": 0,
            "covered_check_ids": [],
            "missing_check_ids": [],
            "top_gaps": [],
        },
        "next_focus": [],
    }


def normalize_continuation_context(value: object) -> dict:
    if not isinstance(value, dict) or value.get("active") is not True:
        return empty_continuation_context()
    coverage = value.get("coverage") if isinstance(value.get("coverage"), dict) else {}
    return {
        "active": True,
        "reason": _contract_string(value.get("reason")),
        "previous_run_id": _contract_string(value.get("previous_run_id")),
        "previous_run_path": _contract_string(value.get("previous_run_path")),
        "previous_run_status": _contract_string(value.get("previous_run_status")),
        "previous_task_verdict": normalize_task_verdict_context(value.get("previous_task_verdict")),
        "previous_task_verdict_path": _contract_string(value.get("previous_task_verdict_path")),
        "previous_evidence_coverage_path": _contract_string(value.get("previous_evidence_coverage_path")),
        "coverage": {
            "status": _contract_string(coverage.get("status")) or "pending",
            "covered_check_count": int_value(coverage.get("covered_check_count")),
            "missing_check_count": int_value(coverage.get("missing_check_count")),
            "target_count": int_value(coverage.get("target_count")),
            "covered_target_count": int_value(coverage.get("covered_target_count")),
            "weak_target_count": int_value(coverage.get("weak_target_count")),
            "missing_target_count": int_value(coverage.get("missing_target_count")),
            "blocked_target_count": int_value(coverage.get("blocked_target_count")),
            "covered_check_ids": _string_list(coverage.get("covered_check_ids")),
            "missing_check_ids": _string_list(coverage.get("missing_check_ids")),
            "top_gaps": _normalize_coverage_gap_rows(coverage.get("top_gaps")),
        },
        "next_focus": _contract_string_list(value.get("next_focus"))[:8],
    }


def normalize_evidence_items(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    items: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        normalized["coverage_results"] = _evidence_coverage_results(normalized.get("coverage_results"))
        items.append(normalized)
    return items


def normalize_evidence_coverage_summary(
    value: object,
    *,
    fallback_covered_check_count: int,
    fallback_missing_check_count: int,
) -> dict:
    source = value if isinstance(value, dict) else {}
    return {
        "status": str(source.get("status") or "pending").strip() or "pending",
        "covered_check_count": int_value(source.get("covered_check_count", fallback_covered_check_count)),
        "missing_check_count": int_value(source.get("missing_check_count", fallback_missing_check_count)),
        "covered_check_ids": _string_list(source.get("covered_check_ids")),
        "missing_check_ids": _string_list(source.get("missing_check_ids")),
        "target_count": int_value(source.get("target_count")),
        "covered_target_count": int_value(source.get("covered_target_count")),
        "weak_target_count": int_value(source.get("weak_target_count")),
        "missing_target_count": int_value(source.get("missing_target_count")),
        "blocked_target_count": int_value(source.get("blocked_target_count")),
        "top_gaps": _normalize_coverage_gap_rows(source.get("top_gaps")),
    }


def normalize_manifest_summary(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    return {
        "claim_count": int_value(source.get("claim_count")),
        "direct_proof_claim_count": int_value(source.get("direct_proof_claim_count")),
        "workspace_artifact_claim_count": int_value(source.get("workspace_artifact_claim_count")),
        "run_artifact_claim_count": int_value(source.get("run_artifact_claim_count")),
        "ledger_only_claim_count": int_value(source.get("ledger_only_claim_count")),
        "unverified_claim_count": int_value(source.get("unverified_claim_count")),
        "problem_count": int_value(source.get("problem_count")),
    }


def normalize_manifest_claims(value: object) -> list[dict]:
    rows: list[dict] = []
    for claim in list(value or []):
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("id") or "").strip()
        if not claim_id:
            continue
        rows.append(
            {
                "id": claim_id,
                "verification_status": str(claim.get("verification_status") or "ledger_only").strip(),
                "measured_evidence": structured_bool_is_true(claim.get("measured_evidence")),
                "concrete_evidence_claim_count": int_value(claim.get("concrete_evidence_claim_count")),
                "artifact_count": int_value(claim.get("artifact_count")),
                "artifact_backed": structured_bool_is_true(claim.get("artifact_backed")),
                "workspace_backed": structured_bool_is_true(claim.get("workspace_backed")),
                "reproducible": structured_bool_is_true(claim.get("reproducible")),
                "coverage_targets": normalize_manifest_claim_coverage_targets(claim.get("coverage_targets")),
                "problem_codes": [str(item).strip() for item in list(claim.get("problem_codes") or []) if str(item).strip()][:20],
            }
        )
    return rows[:40]
