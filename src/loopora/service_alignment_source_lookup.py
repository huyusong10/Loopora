from __future__ import annotations

from pathlib import Path

from loopora.bundles import load_bundle_text, read_bundle_file_text
from loopora.service_alignment_context import alignment_context_option_by_id, alignment_source_option_seed_kind
from loopora.service_alignment_run_source_projection import (
    alignment_run_artifact_paths,
    alignment_run_coverage_summary,
    alignment_run_evidence_summary,
    alignment_run_judgment_contract,
)
from loopora.service_alignment_source_seed import (
    alignment_bundle_source_seed,
    alignment_loop_bundle_id,
    alignment_loop_source_seed,
    alignment_revision_seed_bundle,
    alignment_run_source_seed,
    alignment_session_source_seed,
    alignment_spec_file_source_seed,
)
from loopora.service_types import LooporaConflictError, LooporaError


def resolve_alignment_source_option_seed(service: object, workdir: Path, source_option_id: str) -> dict:
    option_id = str(source_option_id or "").strip()
    if not option_id or option_id == "regenerate":
        return {}
    context = service.get_alignment_workdir_context(workdir)
    option = alignment_context_option_by_id(context["options"], option_id)
    if not option:
        raise LooporaError("selected workdir context is no longer available")
    if option.get("action") == "continue_session":
        raise LooporaConflictError("continue_session options must restore the existing session instead of creating a new one")
    return alignment_source_seed_from_option(service, option)


def alignment_source_seed_from_option(service: object, option: dict) -> dict:
    seed_kind = alignment_source_option_seed_kind(option)
    if seed_kind == "bundle":
        return alignment_source_seed_from_bundle_option(service, option)
    if seed_kind == "run":
        return alignment_source_seed_from_run_option(service, option)
    if seed_kind == "loop":
        return alignment_source_seed_from_loop_option(service, option)
    if seed_kind == "alignment_session":
        return alignment_source_seed_from_alignment_session_option(service, option)
    if seed_kind == "spec_file":
        return alignment_spec_file_source_seed(option)
    raise LooporaError(f"unsupported workdir context source: {seed_kind}")


def alignment_source_seed_from_bundle_option(service: object, option: dict) -> dict:
    bundle_id = str(option.get("source_bundle_id") or "").strip()
    source_bundle = service.export_bundle(bundle_id)
    return alignment_bundle_source_seed(
        option,
        source_bundle,
        seed_bundle=alignment_revision_seed_bundle(source_bundle),
    )


def alignment_source_seed_from_run_option(service: object, option: dict) -> dict:
    run_id = str(option.get("source_run_id") or "").strip()
    run = service.get_run(run_id)
    loop = service.get_loop(run["loop_id"])
    source_bundle_id, source_bundle = alignment_run_source_bundle(
        service,
        run,
        loop,
        fallback_description="Derived as the improvement base for a run selected from workdir context.",
    )
    return alignment_run_source_seed(
        option,
        run,
        source_bundle,
        source_bundle_id=source_bundle_id,
        artifact_paths=alignment_run_artifact_paths(run),
        judgment_contract=alignment_run_judgment_contract(run),
        coverage_summary=alignment_run_coverage_summary(run),
        evidence_summary=alignment_run_evidence_summary(run),
        seed_bundle=alignment_revision_seed_bundle(source_bundle),
    )


def alignment_run_source_bundle(service: object, run: dict, loop: dict, *, fallback_description: str) -> tuple[str, dict]:
    source_bundle_id = alignment_loop_bundle_id(loop)
    if source_bundle_id:
        return source_bundle_id, service.export_bundle(source_bundle_id)
    source_bundle = service.derive_bundle_from_loop(
        run["loop_id"],
        name=str(loop.get("name") or "Run improvement base"),
        description=fallback_description,
        collaboration_summary="Improvement base derived from the current loop.",
    )
    return "", source_bundle


def alignment_source_seed_from_loop_option(service: object, option: dict) -> dict:
    loop_id = str(option.get("source_loop_id") or "").strip()
    loop = service.get_loop(loop_id)
    source_bundle = service.derive_bundle_from_loop(
        loop_id,
        name=str(loop.get("name") or "Loop improvement base"),
        description="Derived as the improvement base for a Loop selected from workdir context.",
        collaboration_summary="Improvement base derived from the current loop.",
    )
    return alignment_loop_source_seed(
        option,
        loop,
        source_bundle,
        seed_bundle=alignment_revision_seed_bundle(source_bundle),
    )


def alignment_source_seed_from_alignment_session_option(service: object, option: dict) -> dict:
    source_session_id = str(option.get("source_alignment_session_id") or "").strip()
    bundle_path = Path(str(option.get("bundle_path") or ""))
    try:
        source_session = service.get_alignment_session(source_session_id)
    except LooporaError:
        source_session = {}
    source_bundle = load_bundle_text(read_bundle_file_text(bundle_path))
    return alignment_session_source_seed(
        option,
        source_session,
        source_bundle,
        seed_bundle=alignment_revision_seed_bundle(source_bundle),
    )
