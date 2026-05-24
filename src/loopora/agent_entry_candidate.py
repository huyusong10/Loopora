from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from loopora.bundles import BundleError, read_bundle_file_text
from loopora.structured_numbers import structured_non_negative_int


def normalized_candidate_yaml(raw_yaml: str) -> str:
    return raw_yaml.rstrip() + "\n" if raw_yaml.strip() else ""


def candidate_yaml_provenance(candidate_text: str) -> dict[str, Any]:
    if not candidate_text:
        return {"candidate_sha256": "", "candidate_bytes": 0}
    data = candidate_text.encode("utf-8")
    return {"candidate_sha256": hashlib.sha256(data).hexdigest(), "candidate_bytes": len(data)}


def ready_candidate_yaml_provenance(session: dict[str, Any]) -> dict[str, Any]:
    empty = {"ready_candidate_sha256": "", "ready_candidate_bytes": 0}
    if str(session.get("status") or "") != "ready":
        return empty
    try:
        candidate_text = normalized_candidate_yaml(read_bundle_file_text(Path(session.get("bundle_path", ""))))
    except (BundleError, OSError, ValueError):
        return empty
    if not candidate_text:
        return empty
    data = candidate_text.encode("utf-8")
    return {"ready_candidate_sha256": hashlib.sha256(data).hexdigest(), "ready_candidate_bytes": len(data)}


def ready_candidate_yaml_provenance_from_validation(session: dict[str, Any]) -> dict[str, Any]:
    validation = session.get("validation") if isinstance(session, dict) else {}
    if not isinstance(validation, dict):
        return {}
    digest = str(validation.get("bundle_sha256") or "").strip()
    try:
        byte_count = int(validation.get("bundle_bytes") or 0)
    except (TypeError, ValueError):
        byte_count = 0
    if not digest or byte_count <= 0:
        return {}
    return {"ready_candidate_sha256": digest, "ready_candidate_bytes": byte_count}


def agent_ready_review_projection(preview: dict[str, Any]) -> dict[str, Any]:
    summary = preview.get("control_summary") if isinstance(preview, dict) else {}
    if not isinstance(summary, dict):
        return {}
    coverage = summary.get("coverage") if isinstance(summary.get("coverage"), dict) else {}
    traceability = summary.get("traceability") if isinstance(summary.get("traceability"), dict) else {}
    diagnostics = [dict(item) for item in list(summary.get("diagnostics") or []) if isinstance(item, dict)]
    gatekeeper = summary.get("gatekeeper") if isinstance(summary.get("gatekeeper"), dict) else {}
    return {
        "loopora_fit_reasons": first_review_items(summary.get("loop_fit_reasons")),
        "success_surface": first_review_items(summary.get("success_surface")),
        "fake_done_risks": first_review_items(summary.get("fake_done_risks")),
        "evidence_preferences": first_review_items(summary.get("evidence_preferences")),
        "execution_strategy": first_review_items(summary.get("execution_strategy")),
        "judgment_tradeoffs": first_review_items(summary.get("judgment_tradeoffs")),
        "residual_risk_policy": first_review_items(summary.get("residual_risk_policy"), limit=1),
        "local_governance": first_review_items(summary.get("local_governance"), limit=1),
        "coverage": {
            "check_count": structured_non_negative_int(coverage.get("check_count"), default=0),
            "target_count": structured_non_negative_int(coverage.get("target_count"), default=0),
            "required_target_count": structured_non_negative_int(coverage.get("required_target_count"), default=0),
        },
        "traceability": {
            "mapped_count": structured_non_negative_int(traceability.get("mapped_count"), default=0),
            "required_count": structured_non_negative_int(traceability.get("required_count"), default=0),
        },
        "gatekeeper": {
            "enabled": gatekeeper.get("enabled") is True,
            "requires_evidence_refs": gatekeeper.get("requires_evidence_refs") is True,
        },
        "diagnostic_count": len([item for item in diagnostics if str(item.get("severity") or "") != "info"]),
    }


def first_review_items(value: object, *, limit: int = 2) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]
