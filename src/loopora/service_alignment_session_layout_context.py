from __future__ import annotations

import logging

from loopora.service_alignment_artifacts import ensure_alignment_artifact_dirs

import json

from loopora.service_alignment_artifacts import alignment_artifact_paths

from loopora.service_cleanup_diagnostics import cleanup_diagnostic_payload, log_cleanup_diagnostic

from loopora.utils import utc_now

from collections.abc import Callable

from dataclasses import dataclass


import shutil

from pathlib import Path

from loopora.db import LooporaRepository

from loopora.diagnostics import get_logger

from loopora.service_alignment_artifacts import (
    alignment_artifact_paths_from_root,
    alignment_artifact_root_from_bundle_path,
    alignment_invocation_dir,
    alignment_output_debug_payload,
    write_alignment_manifest,
)


from collections.abc import MutableMapping


from typing import Protocol

class AlignmentFactorySettings(Protocol):
    role_idle_timeout_seconds: float

class AlignmentFactoryService(Protocol):
    repository: object
    settings: AlignmentFactorySettings
    executor_factory: Callable[[], object]
    _threads: MutableMapping[str, object]

    def _bundle_preview_payload(self, bundle: dict, *, source_path: str = "", validation: dict | None = None) -> dict: ...

    def _mark_local_asset_cleanup_by_path(
        self,
        path: Path,
        *,
        operation: str = "local_asset_cleanup",
        owner_id: object = "",
    ) -> None: ...

    def create_alignment_session(self, *args: object, **raw_request: object) -> dict: ...

    def get_alignment_session(self, session_id: str) -> dict: ...

    def start_alignment_session_async(self, session_id: str) -> None: ...

    def get_alignment_workdir_context(self, workdir: Path) -> dict: ...

    def export_bundle(self, bundle_id: str) -> dict: ...

    def derive_bundle_from_loop(self, request: object, **raw_request: object) -> dict: ...

    def get_loop(self, loop_id: str) -> dict: ...

    def list_loops(self) -> list[dict]: ...

    def get_run(self, run_id: str) -> dict: ...

    def import_bundle_text(
        self,
        raw_text: str,
        *,
        replace_bundle_id: str | None = None,
        imported_from_path: str = "",
    ) -> dict: ...

    def start_run(self, loop_id: str) -> dict: ...

    def start_run_async(self, run_id: str) -> None: ...

logger = get_logger("loopora.service_alignment")

@dataclass(frozen=True)
class AlignmentLegacyLayoutContext:
    repository: LooporaRepository
    ensure_artifact_dirs: Callable[[Path], None]
    append_diagnostic_event: Callable[[str, str, dict], object]

def ensure_alignment_session_layout(context: AlignmentLegacyLayoutContext, session: dict) -> dict:
    bundle_path = Path(session["bundle_path"])
    root = alignment_artifact_root_from_bundle_path(bundle_path)
    paths = alignment_artifact_paths_from_root(root)
    context.ensure_artifact_dirs(root)
    if bundle_path == paths["bundle"]:
        write_alignment_manifest(session)
        return session

    legacy_dir = paths["legacy_dir"]
    legacy_dir.mkdir(parents=True, exist_ok=True)
    _copy_alignment_legacy_file_aliases(root, paths)
    _copy_alignment_legacy_prompts(root)
    _copy_alignment_legacy_outputs(root, paths["bundle"])
    _copy_alignment_legacy_schema(root)
    _copy_alignment_legacy_validations(root)
    _move_alignment_legacy_remainders(context, session, root, legacy_dir)
    updated = context.repository.update_alignment_session(session["id"], bundle_path=str(paths["bundle"]))
    write_alignment_manifest(updated)
    return updated

def _copy_alignment_legacy_file(source: Path, target: Path) -> None:
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

def _copy_alignment_legacy_file_aliases(root: Path, paths: dict[str, Path]) -> None:
    moves: list[tuple[Path, Path]] = [
        (root / "bundle.yml", paths["bundle"]),
        (root / "transcript.jsonl", paths["transcript"]),
        (root / "working_agreement.json", paths["agreement"]),
        (root / "validation.json", paths["validation"]),
    ]
    for source, target in moves:
        _copy_alignment_legacy_file(source, target)

def _copy_alignment_legacy_prompts(root: Path) -> None:
    for prompt_path in sorted(root.glob("alignment_prompt_*.md")):
        attempt = _alignment_attempt_from_legacy_path(prompt_path)
        invocation_dir = alignment_invocation_dir(root, attempt, repair=False)
        invocation_dir.mkdir(parents=True, exist_ok=True)
        _copy_alignment_legacy_file(prompt_path, invocation_dir / "prompt.md")

def _copy_alignment_legacy_outputs(root: Path, bundle_path: Path) -> None:
    for output_path in sorted(root.glob("alignment_output_*.json")):
        attempt = _alignment_attempt_from_legacy_path(output_path)
        invocation_dir = alignment_invocation_dir(root, attempt, repair=False)
        invocation_dir.mkdir(parents=True, exist_ok=True)
        target = invocation_dir / "output.json"
        _copy_alignment_legacy_output(output_path, target, bundle_path)

def _copy_alignment_legacy_output(output_path: Path, target: Path, bundle_path: Path) -> None:
    if target.exists():
        return
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        shutil.copy2(output_path, target)
        return
    target.write_text(
        json.dumps(alignment_output_debug_payload(payload, bundle_path), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

def _copy_alignment_legacy_schema(root: Path) -> None:
    legacy_schema = root / "alignment_schema.json"
    if legacy_schema.exists():
        invocation_dir = alignment_invocation_dir(root, 0, repair=False)
        invocation_dir.mkdir(parents=True, exist_ok=True)
        _copy_alignment_legacy_file(legacy_schema, invocation_dir / "schema.json")

def _copy_alignment_legacy_validations(root: Path) -> None:
    for validation_path in sorted(root.glob("validation_*.json")):
        attempt = _alignment_attempt_from_legacy_path(validation_path)
        invocation_dir = alignment_invocation_dir(root, attempt, repair=False)
        invocation_dir.mkdir(parents=True, exist_ok=True)
        _copy_alignment_legacy_file(validation_path, invocation_dir / "validation.json")

def _move_alignment_legacy_remainders(
    context: AlignmentLegacyLayoutContext,
    session: dict,
    root: Path,
    legacy_dir: Path,
) -> None:
    for source in root.iterdir():
        if source.name in {"conversation", "agreement", "artifacts", "events", "invocations", "legacy"}:
            continue
        if source.name == ".DS_Store":
            continue
        target = legacy_dir / source.name
        if target.exists():
            continue
        try:
            shutil.move(str(source), str(target))
        except OSError as exc:
            diagnostic = cleanup_diagnostic_payload(
                operation="alignment_legacy_artifact_migration",
                resource_type="path",
                resource_id=source,
                owner_id=session["id"],
                error=exc,
                target_path=target,
            )
            log_cleanup_diagnostic(logger, **diagnostic)
            context.append_diagnostic_event(
                session["id"],
                "alignment_legacy_artifact_migration_failed",
                diagnostic,
            )

def _alignment_attempt_from_legacy_path(path: Path) -> int:
    stem = path.stem
    try:
        return max(0, int(stem.rsplit("_", 1)[-1]))
    except (TypeError, ValueError):
        return 0

def append_alignment_diagnostic_event(repository, logger, session_id: str, event_type: str, payload: dict) -> dict:
    try:
        return repository.append_alignment_event(session_id, event_type, payload)
    except Exception as exc:  # noqa: BLE001 - diagnostic event writes must not mask the original operation.
        log_alignment_diagnostic_event_failure(
            logger,
            session_id=session_id,
            event_type=event_type,
            payload=payload,
            error=exc,
        )
        return {}

def append_alignment_local_diagnostic_event(ensure_artifact_dirs, logger, session: dict, event_type: str, payload: dict) -> None:
    try:
        paths = alignment_artifact_paths(session)
        ensure_artifact_dirs(paths["root"])
        event = {
            "id": None,
            "session_id": session["id"],
            "created_at": utc_now(),
            "event_type": event_type,
            "payload": payload,
        }
        with paths["events"].open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 - local diagnostic writes are best-effort fallback evidence.
        log_alignment_diagnostic_event_failure(
            logger,
            session_id=session.get("id", ""),
            event_type=event_type,
            payload=payload,
            error=exc,
        )

def log_alignment_diagnostic_event_failure(
    logger,
    *,
    session_id: str,
    event_type: str,
    payload: dict,
    error: BaseException,
) -> None:
    original_operation = str(payload.get("operation") or "alignment_diagnostic")
    diagnostic = cleanup_diagnostic_payload(
        operation=f"{original_operation}_event_write",
        resource_type="alignment_event",
        resource_id=event_type,
        owner_id=session_id,
        error=error,
        original_operation=original_operation,
    )
    log_cleanup_diagnostic(logger, **diagnostic)


def ensure_alignment_session_layout_from_service(
    service: AlignmentFactoryService,
    logger: logging.Logger,
    session: dict,
) -> dict:
    return ensure_alignment_session_layout(
        AlignmentLegacyLayoutContext(
            repository=service.repository,
            ensure_artifact_dirs=ensure_alignment_artifact_dirs,
            append_diagnostic_event=lambda session_id, event_type, payload: append_alignment_service_diagnostic_event(
                service,
                logger,
                session_id,
                event_type,
                payload,
            ),
        ),
        session,
    )


def append_alignment_service_diagnostic_event(
    service: AlignmentFactoryService,
    logger: logging.Logger,
    session_id: str,
    event_type: str,
    payload: dict,
) -> dict:
    return append_alignment_diagnostic_event(service.repository, logger, session_id, event_type, payload)


def append_alignment_service_local_diagnostic_event(
    logger: logging.Logger,
    session: dict,
    event_type: str,
    payload: dict,
) -> None:
    append_alignment_local_diagnostic_event(ensure_alignment_artifact_dirs, logger, session, event_type, payload)
