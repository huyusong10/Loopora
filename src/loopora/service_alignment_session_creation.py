from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from loopora.branding import state_dir_for_workdir
from loopora.bundles import bundle_to_yaml
from loopora.service_alignment_artifacts import (
    alignment_artifact_paths_from_root,
    alignment_user_message_record,
    write_alignment_transcript_log,
)
from loopora.service_alignment_requests import AlignmentSessionCreateRequest, normalize_alignment_executor_settings
from loopora.service_types import LooporaError
from loopora.utils import make_id, utc_now


class AlignmentSessionCreationRepository(Protocol):
    def create_alignment_session(self, payload: dict) -> dict: ...

    def append_alignment_event(self, session_id: str, event_type: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class AlignmentSessionCreationContext:
    repository: AlignmentSessionCreationRepository
    resolve_source_seed: Callable[[Path, str], dict]
    session_dir: Callable[[Path, str], Path]
    ensure_artifact_dirs: Callable[[Path], None]
    get_session: Callable[[str], dict]
    start_session_async: Callable[[str], None]
    write_transcript_log: Callable[[dict], None] = write_alignment_transcript_log
    id_factory: Callable[[str], str] = make_id
    now: Callable[[], str] = utc_now


def alignment_session_dir(workdir: Path, session_id: str) -> Path:
    return state_dir_for_workdir(workdir) / "alignment_sessions" / session_id


def create_alignment_session(context: AlignmentSessionCreationContext, request: AlignmentSessionCreateRequest) -> dict:
    workdir = request.workdir.expanduser().resolve()
    if not workdir.exists() or not workdir.is_dir():
        raise LooporaError(f"workdir does not exist: {workdir}")
    settings = normalize_alignment_executor_settings(request.executor_settings)
    source_seed = context.resolve_source_seed(workdir, request.source_option_id)
    session_id = context.id_factory("align")
    session_dir = context.session_dir(workdir, session_id)
    paths = alignment_artifact_paths_from_root(session_dir)
    context.ensure_artifact_dirs(session_dir)
    transcript = []
    normalized_message = str(request.message or "").strip()
    if normalized_message:
        transcript.append(alignment_user_message_record(normalized_message, created_at=context.now()).entry)
    session = context.repository.create_alignment_session(
        {
            "id": session_id,
            "status": "idle",
            "workdir": str(workdir),
            "bundle_path": str(paths["bundle"]),
            "transcript": transcript,
            "validation": {},
            "alignment_stage": "clarifying",
            "working_agreement": source_seed.get("working_agreement") or {},
            "executor_session_ref": {},
            "linked_bundle_id": source_seed.get("linked_bundle_id", ""),
            "linked_loop_id": source_seed.get("linked_loop_id", ""),
            "linked_run_id": source_seed.get("linked_run_id", ""),
            **settings,
        }
    )
    seed_bundle = source_seed.get("seed_bundle")
    if isinstance(seed_bundle, dict) and seed_bundle:
        paths["bundle"].write_text(bundle_to_yaml(seed_bundle), encoding="utf-8")
    context.repository.append_alignment_event(
        session_id,
        "alignment_session_created",
        {
            "status": session["status"],
            "workdir": session["workdir"],
            "executor_kind": session["executor_kind"],
        },
    )
    source_event = source_seed.get("event")
    if isinstance(source_event, dict) and source_event:
        context.repository.append_alignment_event(session_id, "alignment_source_context_selected", source_event)
    context.write_transcript_log(context.get_session(session_id))
    if normalized_message and request.start_immediately:
        context.start_session_async(session_id)
        return context.get_session(session_id)
    return context.get_session(session_id)
