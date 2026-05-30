from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
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
from loopora.service_cleanup_diagnostics import cleanup_diagnostic_payload, log_cleanup_diagnostic

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
