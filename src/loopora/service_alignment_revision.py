from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.bundles import bundle_to_yaml
from loopora.service_alignment_artifacts import write_alignment_transcript_log
from loopora.service_alignment_requests import RevisionAlignmentSessionRequest


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
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(bundle_to_yaml(seed_bundle), encoding="utf-8")
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
    context.write_transcript_log(context.get_session(session["id"]))
    if request.start_immediately:
        context.start_session_async(session["id"])
    return context.get_session(session["id"])
