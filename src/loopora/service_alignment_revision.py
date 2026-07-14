from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.bundles import bundle_to_yaml
from loopora.service_bundle_file_writes import write_bundle_text_atomically
from loopora.service_alignment_artifacts import write_alignment_transcript_log, write_alignment_transcript_log_best_effort
from loopora.service_alignment_run_source_projection import (
    alignment_run_artifact_paths,
    alignment_run_coverage_summary,
    alignment_run_evidence_summary,
    alignment_run_judgment_contract,
)
from loopora.service_alignment_source_seed import (
    alignment_bundle_revision_source_context,
    alignment_run_revision_source_context,
    alignment_revision_seed_bundle,
)
from loopora.service_alignment_requests import RevisionAlignmentSessionRequest, RevisionSessionOptions
from loopora.service_types import LooporaError


BUNDLE_REVISION_DEFAULT_MESSAGE = "请先阅读这份已有 Loop 方案，和我对话改进它。先指出你需要确认的最小问题，不要直接生成。"
RUN_REVISION_DEFAULT_MESSAGE = "请基于这次运行的证据和守门裁决，和我对话改进 Loop 方案。先说明最可能要改的治理点，再问我最小必要问题。"
REVISION_SESSION_CREATE_ERROR = "revision session could not be created"


class AlignmentRevisionRepository(Protocol):
    def update_alignment_session(self, session_id: str, **fields: object) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


class AlignmentRevisionSessionCreator(Protocol):
    def __call__(  # noqa: PLR0913 - revision command forwards the existing creation command boundary.
        self,
        *,
        workdir: Path,
        message: str,
        executor_kind: str,
        executor_mode: str,
        command_cli: str,
        command_args_text: str,
        model: str,
        reasoning_effort: str,
        start_immediately: bool,
    ) -> dict: ...


@dataclass(frozen=True)
class AlignmentRevisionContext:
    repository: AlignmentRevisionRepository
    create_session: AlignmentRevisionSessionCreator
    get_session: Callable[[str], dict]
    export_bundle: Callable[[str], dict]
    get_run: Callable[[str], dict]
    get_loop: Callable[[str], dict]
    run_source_bundle: Callable[[dict, dict], tuple[str, dict]]
    start_session_async: Callable[[str], None]
    redact_source_value: Callable[[object], object]
    write_transcript_log: Callable[[dict], None] = write_alignment_transcript_log


def create_revision_alignment_session(context: AlignmentRevisionContext, request: RevisionAlignmentSessionRequest) -> dict:
    seed_bundle = request.seed_bundle
    executor_settings = request.executor_settings
    workdir = Path(seed_bundle["loop"]["workdir"])
    session = context.create_session(
        workdir=workdir,
        message=request.message,
        executor_kind=executor_settings.executor_kind,
        executor_mode=executor_settings.executor_mode,
        command_cli=executor_settings.command_cli,
        command_args_text=executor_settings.command_args_text,
        model=executor_settings.model,
        reasoning_effort=executor_settings.reasoning_effort,
        start_immediately=False,
    )
    bundle_path = Path(session["bundle_path"])
    try:
        write_bundle_text_atomically(bundle_path, bundle_to_yaml(seed_bundle))
    except OSError as exc:
        context.repository.update_alignment_session(
            session["id"],
            status="failed",
            error_message=REVISION_SESSION_CREATE_ERROR,
        )
        context.repository.append_alignment_event(
            session["id"],
            "alignment_bundle_improvement_seed_failed",
            {"status": "failed", "error": REVISION_SESSION_CREATE_ERROR},
        )
        raise LooporaError(REVISION_SESSION_CREATE_ERROR) from exc
    redacted_source = context.redact_source_value(request.source_context)
    working_agreement = {
        "mode": "improvement",
        "source": redacted_source,
        "seed_bundle_metadata": context.redact_source_value(seed_bundle.get("metadata", {})),
    }
    context.repository.update_alignment_session(
        session["id"],
        working_agreement=working_agreement,
        linked_bundle_id=request.linked_bundle_id,
        linked_run_id=request.linked_run_id,
    )
    context.repository.append_alignment_event(
        session["id"],
        "alignment_bundle_improvement_seeded",
        {
            "source_type": redacted_source.get("source_type", "") if isinstance(redacted_source, dict) else "",
            "source_bundle_id": request.linked_bundle_id,
            "source_run_id": request.linked_run_id,
            "bundle_path": str(bundle_path),
        },
    )
    write_alignment_transcript_log_best_effort(
        context.get_session(session["id"]),
        writer=context.write_transcript_log,
    )
    if request.start_immediately:
        context.start_session_async(session["id"])
    return context.get_session(session["id"])


def create_bundle_revision_alignment_session(context: AlignmentRevisionContext, bundle_id: str, request: RevisionSessionOptions) -> dict:
    source_bundle = context.export_bundle(bundle_id)
    seed_bundle = alignment_revision_seed_bundle(source_bundle)
    return create_revision_alignment_session(
        context,
        RevisionAlignmentSessionRequest(
            seed_bundle=seed_bundle,
            message=request.message or BUNDLE_REVISION_DEFAULT_MESSAGE,
            start_immediately=request.start_immediately,
            source_context=alignment_bundle_revision_source_context(bundle_id, source_bundle),
            linked_bundle_id=bundle_id,
            linked_run_id="",
            executor_settings=request.executor_settings,
        ),
    )


def create_run_revision_alignment_session(context: AlignmentRevisionContext, run_id: str, request: RevisionSessionOptions) -> dict:
    run = context.get_run(run_id)
    loop = context.get_loop(run["loop_id"])
    source_bundle_id, source_bundle = context.run_source_bundle(run, loop)
    seed_bundle = alignment_revision_seed_bundle(source_bundle)
    return create_revision_alignment_session(
        context,
        RevisionAlignmentSessionRequest(
            seed_bundle=seed_bundle,
            message=request.message or RUN_REVISION_DEFAULT_MESSAGE,
            start_immediately=request.start_immediately,
            source_context=alignment_run_revision_source_context(
                run_id,
                run,
                source_bundle,
                source_bundle_id=source_bundle_id,
                artifact_paths=alignment_run_artifact_paths(run),
                judgment_contract=alignment_run_judgment_contract(run),
                coverage_summary=alignment_run_coverage_summary(run),
                evidence_summary=alignment_run_evidence_summary(run),
            ),
            linked_bundle_id=source_bundle_id,
            linked_run_id=run_id,
            executor_settings=request.executor_settings,
        ),
    )
