from __future__ import annotations

from collections.abc import Mapping

from loopora.engine.verdict_engine import VerdictEngine
from loopora.kernel import ActorRef, ArtifactRef, LoopContract, StepResult, StepResultStatus
from loopora.kernel.coverage import CoverageState, EvidenceGap, EvidenceTargetState, EvidenceTargetStatus
from loopora.kernel.verdict import Verdict, VerdictBuckets
from loopora.residual_risk_support import meaningful_residual_risks, residual_risk_is_managed, residual_risk_is_meaningful


def verdict_from_legacy_coverage_projection(
    contract: LoopContract,
    *,
    run_id: str,
    coverage_projection: Mapping[str, object],
    raw_verdict: Mapping[str, object] | None = None,
) -> Verdict:
    coverage = coverage_state_from_legacy_projection(
        contract,
        run_id=run_id,
        coverage_projection=coverage_projection,
        raw_verdict=raw_verdict,
    )
    return VerdictEngine().judge(
        contract,
        coverage,
        _gatekeeper_result(run_id, raw_verdict),
    )


def coverage_state_from_legacy_projection(
    contract: LoopContract,
    *,
    run_id: str,
    coverage_projection: Mapping[str, object],
    raw_verdict: Mapping[str, object] | None = None,
) -> CoverageState:
    target_rows = _target_rows_by_id(coverage_projection.get("targets"))
    states = tuple(_target_state(target, target_rows.get(target.id)) for target in contract.evidence_targets)
    return CoverageState(
        run_id=run_id,
        target_states=states,
        top_gaps=_top_gaps(states),
        residual_risks=_residual_risks_for_legacy_projection(coverage_projection, raw_verdict),
    )


def verdict_event_payload_from_kernel_verdict(verdict: Verdict) -> dict:
    payload = {
        "status": verdict.status.value,
        "source": verdict.source.value,
        "summary": verdict.summary,
        "buckets": _verdict_buckets_payload(verdict.buckets),
    }
    if verdict.next_gap:
        payload["next_gap"] = [_gap_payload(gap) for gap in verdict.next_gap]
    return payload


def _target_rows_by_id(value: object) -> dict[str, Mapping[str, object]]:
    rows: dict[str, Mapping[str, object]] = {}
    if not isinstance(value, list):
        return rows
    for item in value:
        if not isinstance(item, Mapping):
            continue
        target_id = str(item.get("id") or item.get("target_id") or "").strip()
        if target_id:
            rows[target_id] = item
    return rows


def _target_state(target, row: Mapping[str, object] | None) -> EvidenceTargetState:
    row = row or {}
    status = _target_status(row.get("status"))
    return EvidenceTargetState(
        target_id=target.id,
        label=str(row.get("label") or target.label or target.id),
        required=bool(row.get("required")) if "required" in row else target.required,
        status=status,
        reason=str(row.get("reason") or _default_target_reason(status)),
        evidence_refs=_string_tuple(row.get("evidence_refs")),
        artifact_refs=_artifact_refs(row.get("artifact_refs")),
    )


def _target_status(value: object) -> EvidenceTargetStatus:
    return {
        "covered": EvidenceTargetStatus.COVERED,
        "weak": EvidenceTargetStatus.WEAK,
        "blocked": EvidenceTargetStatus.BLOCKED,
    }.get(str(value or "missing").strip().lower(), EvidenceTargetStatus.MISSING)


def _default_target_reason(status: EvidenceTargetStatus) -> str:
    if status == EvidenceTargetStatus.COVERED:
        return "Supporting evidence verified this coverage target."
    if status == EvidenceTargetStatus.WEAK:
        return "Evidence for this coverage target is weak or inconclusive."
    if status == EvidenceTargetStatus.BLOCKED:
        return "Evidence reported this coverage target as blocked or failed."
    return "No evidence has verified this coverage target."


def _artifact_refs(value: object) -> tuple[ArtifactRef, ...]:
    refs: list[ArtifactRef] = []
    if not isinstance(value, list):
        return ()
    for item in value:
        if not isinstance(item, Mapping):
            continue
        uri = str(item.get("uri") or item.get("workspace_path") or item.get("path") or "").strip()
        if not uri:
            continue
        refs.append(
            ArtifactRef(
                kind=str(item.get("kind") or "artifact").strip() or "artifact",
                label=str(item.get("label") or item.get("title") or uri).strip() or uri,
                uri=uri,
                content_hash=str(item.get("content_hash") or "").strip() or None,
            )
        )
    return tuple(refs)


def _residual_risks_for_legacy_projection(
    coverage_projection: Mapping[str, object],
    raw_verdict: Mapping[str, object] | None,
) -> tuple[str, ...]:
    risks = _verdict_residual_risk_texts(raw_verdict or {})
    latest_gatekeeper = coverage_projection.get("latest_gatekeeper")
    if isinstance(latest_gatekeeper, Mapping) and str(latest_gatekeeper.get("result") or "").strip().lower() == "passed":
        risks.extend(_string_list(latest_gatekeeper.get("residual_risk")))
    else:
        risks.extend(_strict_string_list(coverage_projection.get("risk_signals")))
    return meaningful_residual_risks(risks)


def _verdict_residual_risk_texts(verdict: Mapping[str, object]) -> list[str]:
    return [*_string_list(verdict.get("residual_risks")), *_string_list(verdict.get("residual_risk"))]


def _gatekeeper_result(run_id: str, raw_verdict: Mapping[str, object] | None) -> StepResult | None:
    if not isinstance(raw_verdict, Mapping) or raw_verdict.get("passed") not in {True, False}:
        return None
    return StepResult(
        run_id=run_id,
        step_id="gatekeeper",
        iteration=0,
        actor=ActorRef.verdict_engine(),
        status=StepResultStatus.COMPLETED if raw_verdict.get("passed") is True else StepResultStatus.FAILED,
        summary=str(raw_verdict.get("decision_summary") or ""),
    )


def _top_gaps(states: tuple[EvidenceTargetState, ...]) -> tuple[EvidenceGap, ...]:
    gaps = [
        EvidenceGap(
            target_id=state.target_id,
            label=state.label,
            status=state.status,
            required=state.required,
            reason=state.reason,
        )
        for state in states
        if state.status != EvidenceTargetStatus.COVERED
    ]
    return tuple(
        sorted(
            gaps,
            key=lambda gap: (
                0 if gap.required else 1,
                {
                    EvidenceTargetStatus.BLOCKED: 0,
                    EvidenceTargetStatus.MISSING: 1,
                    EvidenceTargetStatus.WEAK: 2,
                    EvidenceTargetStatus.COVERED: 3,
                }[gap.status],
                gap.target_id,
            ),
        )
    )


def _verdict_buckets_payload(buckets: VerdictBuckets) -> dict:
    return {
        "proven": [{"label": item} for item in buckets.proven],
        "weak": [{"label": item} for item in buckets.weak],
        "unproven": [{"label": item} for item in buckets.unproven],
        "blocking": [{"label": item} for item in buckets.blocking],
        "residual_risk": [
            {"label": item, "managed": residual_risk_is_managed(item)}
            for item in buckets.residual_risk
            if residual_risk_is_meaningful(item)
        ],
    }


def _gap_payload(gap: EvidenceGap) -> dict:
    return {
        "target_id": gap.target_id,
        "label": gap.label,
        "status": gap.status.value,
        "required": gap.required,
        "reason": gap.reason,
    }


def _string_tuple(value: object) -> tuple[str, ...]:
    return tuple(_string_list(value))


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _strict_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
