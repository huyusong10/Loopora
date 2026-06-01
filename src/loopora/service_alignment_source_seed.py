from __future__ import annotations

import json
from pathlib import Path

from loopora.service_alignment_source_context import (
    alignment_transcript_source_summary as alignment_transcript_source_summary,
    bounded_alignment_file_text as bounded_alignment_file_text,
    redact_alignment_source_value as redact_alignment_source_value,
)


def alignment_bundle_completion_mode(source_bundle: dict) -> str:
    bundle_loop = source_bundle.get("loop") if isinstance(source_bundle.get("loop"), dict) else {}
    return str(bundle_loop.get("completion_mode", "") or "")


def alignment_loop_bundle_id(loop: dict) -> str:
    bundle = loop.get("bundle") if isinstance(loop.get("bundle"), dict) else {}
    return str(bundle.get("id") or "").strip()


def alignment_revision_seed_bundle(source_bundle: dict) -> dict:
    seed = json.loads(json.dumps(source_bundle, ensure_ascii=False))
    metadata = dict(seed.get("metadata") or {})
    metadata["bundle_id"] = ""
    metadata.pop("source_bundle_id", None)
    metadata.pop("revision", None)
    seed["metadata"] = metadata
    return seed


def alignment_source_seed_payload(
    source: dict,
    *,
    seed_bundle: dict | None = None,
    linked_bundle_id: str = "",
    linked_loop_id: str = "",
    linked_run_id: str = "",
) -> dict:
    redacted_source = redact_alignment_source_value(source)
    working_agreement = {
        "mode": str(source.get("mode") or "selected_source"),
        "source": redacted_source,
    }
    if isinstance(seed_bundle, dict) and seed_bundle:
        working_agreement["seed_bundle_metadata"] = redact_alignment_source_value(seed_bundle.get("metadata", {}))
    return {
        "working_agreement": working_agreement,
        "seed_bundle": seed_bundle or {},
        "linked_bundle_id": linked_bundle_id,
        "linked_loop_id": linked_loop_id,
        "linked_run_id": linked_run_id,
        "event": {
            "source_type": redacted_source.get("source_type", "") if isinstance(redacted_source, dict) else "",
            "source_bundle_id": redacted_source.get("source_bundle_id", "") if isinstance(redacted_source, dict) else "",
            "source_loop_id": redacted_source.get("source_loop_id", "") if isinstance(redacted_source, dict) else "",
            "source_run_id": redacted_source.get("source_run_id", "") if isinstance(redacted_source, dict) else "",
            "source_alignment_session_id": redacted_source.get("source_alignment_session_id", "") if isinstance(redacted_source, dict) else "",
            "spec_path": redacted_source.get("spec_path", "") if isinstance(redacted_source, dict) else "",
            "reason": redacted_source.get("reason", "") if isinstance(redacted_source, dict) else "",
        },
    }


def alignment_spec_file_source_seed(option: dict) -> dict:
    spec_path = Path(str(option.get("spec_path") or ""))
    source = {
        "mode": "selected_source",
        "source_type": "spec_file",
        "spec_path": str(spec_path),
        "reason": "start_from_workdir_spec",
        "spec_markdown": bounded_alignment_file_text(spec_path),
        "artifact_paths": {"spec": str(spec_path)},
    }
    return alignment_source_seed_payload(source)


def alignment_bundle_source_seed(option: dict, source_bundle: dict, *, seed_bundle: dict | None = None) -> dict:
    bundle_id = str(option.get("source_bundle_id") or "").strip()
    source = {
        "mode": "improvement",
        "source_type": "bundle",
        "source_bundle_id": bundle_id,
        "source_loop_id": str(option.get("source_loop_id") or source_bundle.get("loop_id") or ""),
        "source_run_id": "",
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_workdir_context",
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }
    return alignment_source_seed_payload(source, seed_bundle=seed_bundle, linked_bundle_id=bundle_id)


def alignment_bundle_revision_source_context(bundle_id: str, source_bundle: dict) -> dict:
    return {
        "mode": "improvement",
        "source_type": "bundle",
        "source_bundle_id": str(bundle_id or ""),
        "source_run_id": "",
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_imported_bundle",
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }


def alignment_loop_source_seed(
    option: dict,
    loop: dict,
    source_bundle: dict,
    *,
    seed_bundle: dict | None = None,
) -> dict:
    loop_id = str(option.get("source_loop_id") or "").strip()
    source = {
        "mode": "improvement",
        "source_type": "loop",
        "source_bundle_id": "",
        "source_loop_id": loop_id,
        "source_run_id": "",
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_workdir_loop",
        "source_loop_name": str(loop.get("name") or ""),
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }
    return alignment_source_seed_payload(source, seed_bundle=seed_bundle, linked_loop_id=loop_id)


def alignment_run_source_seed(  # noqa: PLR0913 - run source seeds expose explicit projection inputs from service lookup.
    option: dict,
    run: dict,
    source_bundle: dict,
    *,
    source_bundle_id: str = "",
    artifact_paths: dict | None = None,
    judgment_contract: dict | None = None,
    coverage_summary: dict | None = None,
    evidence_summary: list | None = None,
    seed_bundle: dict | None = None,
) -> dict:
    run_id = str(option.get("source_run_id") or "").strip()
    loop_id = str(run.get("loop_id") or "")
    source = {
        "mode": "improvement",
        "source_type": "run",
        "source_bundle_id": source_bundle_id,
        "source_loop_id": loop_id,
        "source_run_id": run_id,
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_workdir_run_evidence",
        "run_status": str(run.get("status") or ""),
        "artifact_paths": artifact_paths or {},
        "judgment_contract": judgment_contract or {},
        "coverage_summary": coverage_summary or {},
        "evidence_summary": evidence_summary or [],
        "task_verdict": run.get("task_verdict") or {},
        "gatekeeper_verdict": run.get("last_verdict_json") or {},
    }
    return alignment_source_seed_payload(
        source,
        seed_bundle=seed_bundle,
        linked_bundle_id=source_bundle_id,
        linked_loop_id=loop_id,
        linked_run_id=run_id,
    )


def alignment_run_revision_source_context(  # noqa: PLR0913 - run revision context exposes explicit projection inputs.
    run_id: str,
    run: dict,
    source_bundle: dict,
    *,
    source_bundle_id: str = "",
    artifact_paths: dict | None = None,
    judgment_contract: dict | None = None,
    coverage_summary: dict | None = None,
    evidence_summary: list | None = None,
) -> dict:
    return {
        "mode": "improvement",
        "source_type": "run",
        "source_bundle_id": source_bundle_id,
        "source_run_id": str(run_id or ""),
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_run_evidence",
        "run_status": str(run.get("status") or ""),
        "artifact_paths": artifact_paths or {},
        "judgment_contract": judgment_contract or {},
        "coverage_summary": coverage_summary or {},
        "evidence_summary": evidence_summary or [],
        "task_verdict": run.get("task_verdict") or {},
        "gatekeeper_verdict": run.get("last_verdict_json") or {},
    }


def alignment_session_source_seed(
    option: dict,
    source_session: dict,
    source_bundle: dict,
    *,
    seed_bundle: dict | None = None,
) -> dict:
    source_session_id = str(option.get("source_alignment_session_id") or "").strip()
    bundle_path = Path(str(option.get("bundle_path") or ""))
    source = {
        "mode": "improvement",
        "source_type": str(option.get("source_type") or "alignment_session"),
        "source_alignment_session_id": source_session_id,
        "source_bundle_id": "",
        "source_loop_id": "",
        "source_run_id": "",
        "source_completion_mode": alignment_bundle_completion_mode(source_bundle),
        "reason": "improve_from_workdir_alignment_session",
        "source_status": str(source_session.get("status") or option.get("status") or ""),
        "source_bundle_path": str(bundle_path),
        "transcript_summary": alignment_transcript_source_summary(source_session) if source_session else [],
        "run_status": "",
        "evidence_summary": [],
        "task_verdict": {},
        "gatekeeper_verdict": {},
    }
    return alignment_source_seed_payload(source, seed_bundle=seed_bundle)
