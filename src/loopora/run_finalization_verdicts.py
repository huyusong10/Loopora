from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from loopora.compiler import compile_loop_contract
from loopora.engine import verdict_event_payload_from_kernel_verdict, verdict_from_legacy_coverage_projection
from loopora.evidence_coverage import load_or_build_evidence_coverage_projection
from loopora.run_artifacts import RunArtifactLayout


def kernel_event_verdict_for_finalization(
    *,
    run_id: str,
    existing_run: Mapping[str, object],
    run_dir: Path,
    last_verdict: object,
) -> dict:
    compiled_spec = _mapping(existing_run.get("compiled_spec") or existing_run.get("compiled_spec_json"))
    if not compiled_spec:
        return {}
    try:
        coverage = load_or_build_evidence_coverage_projection(RunArtifactLayout(run_dir))
    except (OSError, UnicodeError, ValueError):
        return {}
    if not isinstance(coverage.get("targets"), list):
        return {}
    loop_id = str(existing_run.get("loop_id") or run_id).strip() or run_id
    completion_mode = str(existing_run.get("completion_mode") or "gatekeeper").strip() or "gatekeeper"
    verdict = verdict_from_legacy_coverage_projection(
        compile_loop_contract(loop_id, compiled_spec, completion_mode=completion_mode),
        run_id=run_id,
        coverage_projection=coverage,
        raw_verdict=_mapping(last_verdict),
    )
    return verdict_event_payload_from_kernel_verdict(verdict)


def event_verdict_for_finalization(*, public_task_verdict: Mapping[str, object], kernel_event_verdict: Mapping[str, object]) -> dict:
    if not kernel_event_verdict:
        return dict(public_task_verdict)
    return {
        **dict(kernel_event_verdict),
        **dict(public_task_verdict),
        "next_gap": kernel_event_verdict.get("next_gap") or public_task_verdict.get("next_gap") or [],
    }


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}
