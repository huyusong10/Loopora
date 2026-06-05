from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from loopora.coverage_target_semantics import coverage_target_is_required
from loopora.evidence_manifest_artifacts import dedupe_artifact_refs
from loopora.residual_risk_support import (
    residual_risk_is_managed,
    residual_risk_is_meaningful,
    residual_risk_text_matches_or_previews_any,
    residual_risk_policy_disallows_acceptance,
)

BUCKET_KEYS = ("proven", "weak", "unproven", "blocking", "residual_risk")
TARGET_STATUS_BUCKETS = {
    "covered": "proven",
    "weak": "weak",
    "blocked": "blocking",
}
DISALLOWED_RESIDUAL_RISK_REASON = (
    "Residual risk was reported even though the run contract disallows accepted residual risk."
)


def build_task_verdict_buckets(
    coverage: Mapping[str, Any],
    verdict: Mapping[str, Any],
    compiled_spec: Mapping[str, Any],
) -> dict[str, list[dict]]:
    buckets = _empty_buckets()
    residual_risk_acceptance_allowed = not residual_risk_policy_disallows_acceptance(
        compiled_spec.get("residual_risk")
    )
    _append_coverage_target_buckets(buckets, coverage.get("targets"))
    _append_verdict_blockers(buckets, verdict)
    _append_residual_risk_buckets(
        buckets,
        _coverage_risk_signals_for_buckets(coverage, verdict),
        acceptance_allowed=residual_risk_acceptance_allowed,
    )
    _append_verdict_residual_risk_buckets(
        buckets,
        verdict,
        acceptance_allowed=residual_risk_acceptance_allowed,
    )
    if not any(buckets.values()):
        _append_legacy_evidence_buckets(buckets, verdict)
    return {key: _dedupe_bucket_items(items)[:12] for key, items in buckets.items()}


def bucket_list(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    result: list[dict] = []
    for item in value:
        if isinstance(item, Mapping):
            result.append(dict(item))
        elif isinstance(item, str) and item.strip():
            result.append({"label": item.strip()})
    return result


def clean_text(value: object, *, max_length: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) > max_length:
        return text[: max_length - 1].rstrip() + "..."
    return text


def string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def verdict_blockers(verdict: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    blockers.extend(string_list(verdict.get("blocking_issues")))
    blockers.extend(string_list(verdict.get("hard_constraint_violations")))
    blockers.extend(string_list(verdict.get("failed_check_ids")))
    for failure in list(verdict.get("priority_failures") or []):
        if isinstance(failure, Mapping):
            text = clean_text(failure.get("summary") or failure.get("error_code"), max_length=240)
            if text:
                blockers.append(text)
    return list(dict.fromkeys(blockers))


def verdict_residual_risk_texts(verdict: Mapping[str, Any]) -> list[str]:
    return [*string_list(verdict.get("residual_risks")), *string_list(verdict.get("residual_risk"))]


def _empty_buckets() -> dict[str, list[dict]]:
    return {key: [] for key in BUCKET_KEYS}


def _append_coverage_target_buckets(buckets: dict[str, list[dict]], targets: object) -> None:
    for target in list(targets or []):
        if not isinstance(target, Mapping):
            continue
        buckets[_bucket_for_target(target)].append(_target_bucket_item(target))


def _target_bucket_item(target: Mapping[str, Any]) -> dict:
    return {
        "id": str(target.get("id") or ""),
        "label": str(target.get("label") or target.get("id") or ""),
        "text": clean_text(target.get("text"), max_length=240),
        "reason": clean_text(target.get("reason"), max_length=240),
        "evidence_refs": _strict_string_list(target.get("evidence_refs")),
        "artifact_refs": _mapping_list(target.get("artifact_refs"), limit=12),
        "required": coverage_target_is_required(target),
    }


def _bucket_for_target(target: Mapping[str, Any]) -> str:
    status = str(target.get("status") or "").strip().lower()
    return TARGET_STATUS_BUCKETS.get(status, "unproven")


def _append_verdict_blockers(buckets: dict[str, list[dict]], verdict: Mapping[str, Any]) -> None:
    for blocker in verdict_blockers(verdict):
        buckets["blocking"].append({"label": blocker, "reason": "Reported by the latest raw verdict."})


def _append_residual_risk_buckets(
    buckets: dict[str, list[dict]],
    risk_signals: object,
    *,
    acceptance_allowed: bool,
) -> None:
    for risk in _strict_string_list(risk_signals):
        text = clean_text(risk, max_length=240)
        if not acceptance_allowed and residual_risk_is_meaningful(text):
            buckets["weak"].append(
                {
                    "label": text,
                    "reason": DISALLOWED_RESIDUAL_RISK_REASON,
                    "residual_risk_policy": "disallowed",
                }
            )
        elif residual_risk_is_managed(text):
            buckets["residual_risk"].append({"label": text, "managed": True})
        elif residual_risk_is_meaningful(text):
            buckets["weak"].append(
                {
                    "label": text,
                    "reason": "Residual risk was observed without enough management detail to accept it.",
                    "managed": False,
                }
            )


def _coverage_risk_signals_for_buckets(
    coverage: Mapping[str, Any],
    verdict: Mapping[str, Any],
) -> list[str]:
    raw_verdict_risks = verdict_residual_risk_texts(verdict)
    latest_gatekeeper = coverage.get("latest_gatekeeper")
    if (
        isinstance(latest_gatekeeper, Mapping)
        and str(latest_gatekeeper.get("result") or "").strip().lower() == "passed"
    ):
        risks = string_list(latest_gatekeeper.get("residual_risk"))
    else:
        risks = _strict_string_list(coverage.get("risk_signals"))
    return [risk for risk in risks if not residual_risk_text_matches_or_previews_any(risk, raw_verdict_risks)]


def _append_verdict_residual_risk_buckets(
    buckets: dict[str, list[dict]],
    verdict: Mapping[str, Any],
    *,
    acceptance_allowed: bool,
) -> None:
    for risk in verdict_residual_risk_texts(verdict):
        if not acceptance_allowed and residual_risk_is_meaningful(risk):
            buckets["weak"].append(
                {
                    "label": clean_text(risk, max_length=240),
                    "reason": DISALLOWED_RESIDUAL_RISK_REASON,
                    "residual_risk_policy": "disallowed",
                }
            )
        elif residual_risk_is_managed(risk):
            buckets["residual_risk"].append(
                {"label": clean_text(risk, max_length=240), "managed": True}
            )
        elif residual_risk_is_meaningful(risk):
            buckets["weak"].append(
                {
                    "label": clean_text(risk, max_length=240),
                    "reason": "Residual risk was reported without enough management detail to accept it.",
                    "managed": False,
                }
            )


def _append_legacy_evidence_buckets(buckets: dict[str, list[dict]], verdict: Mapping[str, Any]) -> None:
    for claim in string_list(verdict.get("evidence_claims")):
        buckets["proven"].append({"label": clean_text(claim, max_length=240)})
    for ref in string_list(verdict.get("evidence_refs")):
        buckets["proven"].append({"label": ref, "reason": "Referenced by the latest raw verdict."})


def _strict_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _mapping_list(value: object, *, limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    return dedupe_artifact_refs([dict(item) for item in value if isinstance(item, Mapping)])[:limit]


def _dedupe_bucket_items(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for item in items:
        key = "|".join(
            [
                str(item.get("id") or ""),
                str(item.get("label") or ""),
                str(item.get("text") or ""),
                str(item.get("reason") or ""),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
